"""
Response schemas.

The response is shaped to map onto the frontend's existing
AnalysisResult contract (basirah/src/types/analysis.ts) as closely as
possible, with two deliberate differences that are handled by a small
frontend adapter rather than by duplicating the whole type:

  1. The frontend's `dna` is Record<DnaAxis, number>. A URL-only
     analysis has no synthetic-media or provenance evidence, so those
     axes are returned as `null` here rather than as invented numbers.

  2. Graph node labels carry both languages inline, matching the
     frontend's labelEn/labelAr pairs.

Everything else — trustScore, riskLevel, confidence, primarySignal,
secondarySignals, timeline, lanes — aligns field-for-field.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureObservation(BaseModel):
    """One measured feature, exposed for transparency."""

    name: str
    value: float


class HeuristicFindingResponse(BaseModel):
    """One rule outcome, triggered or not."""

    id: str
    title: str
    severity: str
    weight: int
    triggered: bool
    explanation: str


class EvidenceNodeResponse(BaseModel):
    id: str
    labelEn: str
    labelAr: str
    detailEn: str
    detailAr: str
    weight: str = Field(description="primary | secondary")
    polarity: str = Field(description="risk | neutral | trust")
    x: float
    y: float


class EvidenceEdgeResponse(BaseModel):
    from_: str = Field(alias="from")
    to: str
    relation: str = Field(description="asserts | contradicts | derives")

    model_config = {"populate_by_name": True}


class EvidenceGraphResponse(BaseModel):
    nodes: list[EvidenceNodeResponse]
    edges: list[EvidenceEdgeResponse]


class PrimarySignalResponse(BaseModel):
    titleEn: str
    titleAr: str
    bodyEn: str
    bodyAr: str


class SecondarySignalResponse(BaseModel):
    id: str
    metricKey: str
    valueEn: str
    valueAr: str
    severity: str


class TimelineEntryResponse(BaseModel):
    id: str
    stage: str
    offsetSeconds: float


class RiskBreakdown(BaseModel):
    """Every intermediate value of the fusion, for auditability."""

    modelRisk: float = Field(description="0-100, model only")
    heuristicRisk: float = Field(description="0-100, heuristics only")
    finalRisk: float = Field(description="0-100, fused")
    modelWeight: float
    heuristicWeight: float
    formula: str = Field(
        description="Human-readable form of the fusion actually applied."
    )


class URLAnalysisResponse(BaseModel):
    """The payload consumed by the BASIRAH frontend."""

    # --- frontend contract ---
    isMock: bool = Field(
        description="False: this result came from the real analysis pipeline."
    )
    source: str = Field(description="'live' | 'mock'")
    engine: str
    engineVersion: str
    signal: dict[str, str]
    trustScore: float = Field(description="0-100, higher is more trustworthy")
    riskLevel: str = Field(description="trusted | caution | high_risk")
    confidence: float = Field(description="0-100, confidence in the assessment")
    dna: dict[str, int | None] = Field(
        description=(
            "Trust DNA axes. synthetic/provenance are null for URL-only "
            "analysis because no such evidence exists — they are NOT "
            "invented."
        )
    )
    graph: EvidenceGraphResponse
    timeline: list[TimelineEntryResponse]
    primarySignal: PrimarySignalResponse | None
    secondarySignals: list[SecondarySignalResponse]
    lanes: list[str]
    durationMs: float

    # --- Phase 2 transparency extras (ignored by the Phase 1 UI) ---
    normalizedUrl: str
    modelAvailable: bool
    modelNote: str
    heuristicFindings: list[HeuristicFindingResponse]
    riskBreakdown: RiskBreakdown
    featureObservations: list[FeatureObservation]


class ModelInfoResponse(BaseModel):
    """Transparency metadata. Exposes no filesystem paths."""

    available: bool
    reason: str
    modelName: str | None = None
    modelVersion: str | None = None
    featureCount: int
    features: list[str]
    metrics: dict[str, float] | None = Field(
        description=(
            "Evaluation metrics from training. Null when no model has been "
            "trained — never fabricated."
        )
    )
    datasetRows: int | None = None
    trainedAt: str | None = None

    # --- Phase 2E additions -------------------------------------------
    # Declared rather than attached dynamically: pydantic v2 rejects
    # setattr on an undeclared field, and silently dropping these would
    # remove exactly the disclosure the promotion decision depends on.
    fit_for_automated_blocking: bool = Field(
        default=False,
        description=(
            "Whether this model is cleared for automated enforcement. "
            "False means the verdict is advisory and must be reviewed by a "
            "human before any blocking action."
        ),
    )
    notice: str | None = Field(
        default=None,
        description="Plain-language safety statement for API consumers.",
    )
    training_corpora: list[str] | None = None
    held_out_corpora: list[str] | None = None
    selected_threshold: float | None = None
    selected_configuration: str | None = None


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: str
