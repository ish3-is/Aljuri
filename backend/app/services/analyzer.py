"""
URL analysis orchestration.

Runs the pipeline in order and assembles the frontend-facing response:
normalize -> extract -> heuristics -> inference -> fusion -> explain.
"""

from __future__ import annotations

import time
from dataclasses import asdict

from app.core.config import settings
from app.ml.production import InferenceResult, predict_risk_production
from app.schemas.responses import (
    ErrorResponse,
    EvidenceEdgeResponse,
    EvidenceGraphResponse,
    EvidenceNodeResponse,
    FeatureObservation,
    HeuristicFindingResponse,
    PrimarySignalResponse,
    RiskBreakdown,
    SecondarySignalResponse,
    TimelineEntryResponse,
    URLAnalysisResponse,
)
from app.services import explanation_engine as explain
from app.services.feature_extractor import FEATURE_NAMES, extract_features
from app.services.heuristic_engine import (
    HeuristicFinding,
    evaluate,
    heuristic_risk,
)
from app.services.risk_engine import RiskAssessment, fuse
from app.services.url_analyzer import InvalidURLError, NormalizedURL, normalize

ENGINE_NAME = "basirah-url-intelligence"
ENGINE_VERSION = "2.0.0"


class URLAnalysisError(Exception):
    """Wraps InvalidURLError with the HTTP status the API should return."""

    def __init__(self, error: InvalidURLError) -> None:
        super().__init__(error.message)
        self.payload = ErrorResponse(
            error="invalid_url", code=error.code, detail=error.message
        )


def analyze_url(raw_url: str) -> URLAnalysisResponse:
    """Run the full pipeline for one URL."""
    started = time.perf_counter()

    # 1. Normalize (raises InvalidURLError for anything unsafe/unusable)
    try:
        url = normalize(raw_url)
    except InvalidURLError as exc:
        raise URLAnalysisError(exc) from exc

    # 2. Deterministic feature extraction
    features = extract_features(url)

    # 3. Explainable heuristics
    findings = evaluate(url)
    heuristic_score, _fired = heuristic_risk(findings)

    # 4. Model inference — may be unavailable, which is reported honestly
    prediction = predict_risk_production(url)

    # 5. Risk fusion
    assessment = fuse(prediction, heuristic_score, findings)

    duration_ms = (time.perf_counter() - started) * 1000.0

    # 6. Explanation
    primary = explain.build_primary_signal(url, findings, assessment, prediction)
    secondary = explain.build_secondary_signals(url, findings, features, prediction)
    timeline = explain.build_timeline(duration_ms)
    dna = explain.map_to_trust_dna(url, findings, features, assessment)
    graph = build_evidence_graph(url, findings, assessment, prediction)

    return URLAnalysisResponse(
        # --- frontend contract ---
        isMock=False,
        source="live",
        engine=ENGINE_NAME,
        engineVersion=ENGINE_VERSION,
        signal={
            "kind": "url",
            "valueEn": url.normalized,
            "valueAr": url.normalized,
        },
        trustScore=assessment.trust_score,
        riskLevel=assessment.risk_level,
        confidence=assessment.confidence,
        dna=dna,
        graph=graph,
        timeline=[
            TimelineEntryResponse(id=f"s{i}", stage=r.stage, offsetSeconds=r.offset_seconds)
            for i, r in enumerate(timeline)
        ],
        primarySignal=(
            PrimarySignalResponse(
                titleEn=primary.title_en,
                titleAr=primary.title_ar,
                bodyEn=primary.body_en,
                bodyAr=primary.body_ar,
            )
            if primary
            else None
        ),
        secondarySignals=[
            SecondarySignalResponse(
                id=s.id,
                metricKey=s.metric_key,
                valueEn=s.value_en,
                valueAr=s.value_ar,
                severity=s.severity,
            )
            for s in secondary
        ],
        lanes=["url_intelligence", "identity", "metadata"],
        durationMs=round(duration_ms, 2),
        # --- transparency extras ---
        normalizedUrl=url.normalized,
        modelAvailable=prediction.available,
        modelNote=prediction.reason,
        heuristicFindings=[
            HeuristicFindingResponse(**_finding_to_dict(f)) for f in findings
        ],
        riskBreakdown=RiskBreakdown(
            modelRisk=assessment.model_risk,
            heuristicRisk=assessment.heuristic_risk,
            finalRisk=assessment.final_risk,
            modelWeight=assessment.model_weight_used,
            heuristicWeight=assessment.heuristic_weight_used,
            formula=_formula(assessment, prediction),
        ),
        featureObservations=[
            FeatureObservation(name=name, value=float(features[name]))
            for name in FEATURE_NAMES
        ],
    )


def _finding_to_dict(finding: HeuristicFinding) -> dict[str, object]:
    return asdict(finding)


def _formula(assessment: RiskAssessment, prediction: InferenceResult) -> str:
    """State exactly which formula ran, so the defense has no ambiguity."""
    if prediction.available:
        return (
            f"final_risk = {assessment.model_weight_used} x model_risk "
            f"+ {assessment.heuristic_weight_used} x heuristic_risk "
            f"= {assessment.model_weight_used} x {assessment.model_risk} "
            f"+ {assessment.heuristic_weight_used} x {assessment.heuristic_risk} "
            f"= {assessment.final_risk}; trust_score = 100 - final_risk "
            f"= {assessment.trust_score}"
        )
    return (
        "final_risk = 1.0 x heuristic_risk = "
        f"{assessment.final_risk} (no trained model available; the model "
        "term is inactive and heuristics carry full weight); "
        f"trust_score = 100 - final_risk = {assessment.trust_score}"
    )


# ====================================================================
# EVIDENCE GRAPH
# ====================================================================
# The graph is built from the rules that actually fired, so it always
# describes THIS analysis. Layout is a fixed vertical spine: input ->
# observation -> conclusion. Positions are percentages of the graph's
# own coordinate space.


def build_evidence_graph(
    url: NormalizedURL,
    findings: list[HeuristicFinding],
    assessment: RiskAssessment,
    prediction: InferenceResult,
) -> EvidenceGraphResponse:
    fired = [f for f in findings if f.triggered]

    nodes: list[EvidenceNodeResponse] = [
        EvidenceNodeResponse(
            id="input",
            labelEn="Submitted URL",
            labelAr="الرابط المُرسل",
            detailEn=f"Analysis performed on the URL string alone. No page "
            f"content was requested or fetched. Normalized to: {url.normalized}",
            detailAr=f"تم التحليل على نص الرابط فقط، دون طلب أو جلب أي محتوى "
            f"للصفحة. بعد التوحيد: {url.normalized}",
            weight="primary",
            polarity="neutral",
            x=50,
            y=8,
        )
    ]
    edges: list[EvidenceEdgeResponse] = []

    # Up to four fired rules become graph nodes, strongest first.
    for index, finding in enumerate(fired[:4]):
        node_id = f"finding-{finding.id.lower()}"
        nodes.append(
            EvidenceNodeResponse(
                id=node_id,
                labelEn=finding.title,
                labelAr=_ar_title(finding.id),
                detailEn=finding.explanation,
                detailAr=_ar_detail(finding.id, finding.title),
                weight="primary" if finding.severity == "high" else "secondary",
                polarity="risk",
                x=20 + (index % 2) * 60,
                y=32 + index * 15,
            )
        )
        edges.append(EvidenceEdgeResponse(**{"from": "input", "to": node_id}, relation="derives"))

    # Conclusion node.
    conclusion_id = "risk-assessment"
    nodes.append(
        EvidenceNodeResponse(
            id=conclusion_id,
            labelEn="Risk assessment",
            labelAr="تقييم الخطورة",
            detailEn=f"{len(fired)} indicator(s) contributed to a fused risk "
            f"value of {assessment.final_risk:.0f}/100, giving a trust score "
            f"of {assessment.trust_score:.0f}/100. This is an indicator-based "
            f"assessment, not a confirmation that the site is harmful.",
            detailAr=f"أسهم {len(fired)} مؤشرًا في قيمة خطورة مدمجة قدرها "
            f"{assessment.final_risk:.0f}/100، أي درجة ثقة "
            f"{assessment.trust_score:.0f}/100. هذا تقييم قائم على المؤشرات، "
            f"وليست تأكيدًا على أن الموقع ضار.",
            weight="primary",
            polarity=(
                "risk"
                if assessment.risk_level == "high_risk"
                else "neutral"
                if assessment.risk_level == "caution"
                else "trust"
            ),
            x=50,
            y=88,
        )
    )
    for index, finding in enumerate(fired[:4]):
        edges.append(
            EvidenceEdgeResponse(
                **{"from": f"finding-{finding.id.lower()}", "to": conclusion_id},
                relation="derives",
            )
        )

    # Always keep at least a spine so the graph is never empty.
    if not fired:
        nodes.append(
            EvidenceNodeResponse(
                id="no-indicators",
                labelEn="No strong indicators",
                labelAr="لا توجد مؤشرات قوية",
                detailEn="None of the structural checks fired for this URL.",
                detailAr="لم يُفعَّل أي فحص بنيوي لهذا الرابط.",
                weight="secondary",
                polarity="trust",
                x=50,
                y=50,
            )
        )
        edges.append(
            EvidenceEdgeResponse(
                **{"from": "input", "to": "no-indicators"}, relation="derives"
            )
        )
        edges.append(
            EvidenceEdgeResponse(
                **{"from": "no-indicators", "to": conclusion_id},
                relation="derives",
            )
        )

    return EvidenceGraphResponse(nodes=nodes, edges=edges)


def _ar_title(rule_id: str) -> str:
    return explain.ARABIC_TITLES.get(rule_id, rule_id)


def _ar_detail(rule_id: str, fallback: str) -> str:
    return explain.ARABIC_EXPLANATIONS.get(rule_id, fallback)
