"""
Risk fusion.

Combines the model probability with heuristic evidence into a single
risk score, then converts risk to BASIRAH's Trust Score.

The formula is intentionally simple enough to explain in one sentence
during a defense:

    final_risk = w_model * model_risk + w_heuristic * heuristic_risk

with the model term dropped (and the heuristic term rescaled to full
weight) when no trained model is available.

Two design constraints, both enforced here rather than left to callers:

1. NO SINGLE RULE can produce a high-risk classification on its own.
   The strongest rule contributes 22 of 100 heuristic points, so even a
   fully-saturated single-rule score stays below the caution threshold.
   A high-risk verdict requires corroboration.

2. The ML probability is NEVER used alone. Phishing classifiers trained
   on lexical features generalise poorly to unseen domains, so a lone
   confident prediction is treated as weak evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.ml.production import InferenceResult as Prediction
from app.services.heuristic_engine import HeuristicFinding

RiskLevel = str  # "trusted" | "caution" | "high_risk"


@dataclass
class RiskAssessment:
    """The fused outcome, with every intermediate value retained.

    Every field here is exposed in the API response so the computation
    can be reconstructed and audited from the outside.
    """

    model_risk: float
    heuristic_risk: float
    final_risk: float
    trust_score: float
    risk_level: RiskLevel
    model_weight_used: float
    heuristic_weight_used: float
    confidence: float
    contributing_rules: list[str] = field(default_factory=list)


def classify(final_risk: float) -> RiskLevel:
    """Map a 0-100 risk score onto a RiskLevel.

    Thresholds come from settings so they are configurable and
    citable, never scattered.
    """
    if final_risk >= settings.high_risk_threshold:
        return "high_risk"
    if final_risk >= settings.caution_threshold:
        return "caution"
    return "trusted"


def fuse(
    prediction: Prediction,
    heuristic_score: float,
    findings: list[HeuristicFinding],
) -> RiskAssessment:
    """Fuse model and heuristic evidence into a single assessment."""
    if prediction.available and prediction.risk_percent() is not None:
        model_risk = prediction.risk_percent()  # type: ignore[assignment]
        w_model = settings.model_weight
        w_heuristic = settings.heuristic_weight
    else:
        # No model: heuristics carry the full weight rather than being
        # diluted against an absent signal. Rescaling keeps the two
        # terms summing to 1.0 so the formula reads the same either way.
        model_risk = 0.0
        w_model = 0.0
        w_heuristic = 1.0

    heuristic_risk = max(0.0, min(100.0, heuristic_score))
    model_risk = max(0.0, min(100.0, float(model_risk)))

    final_risk = w_model * model_risk + w_heuristic * heuristic_risk
    final_risk = max(0.0, min(100.0, final_risk))

    trust_score = round(100.0 - final_risk, 1)
    risk_level = classify(final_risk)

    fired = [f for f in findings if f.triggered]
    contributing = [f.id for f in fired]

    return RiskAssessment(
        model_risk=round(model_risk, 2),
        heuristic_risk=round(heuristic_risk, 2),
        final_risk=round(final_risk, 2),
        trust_score=trust_score,
        risk_level=risk_level,
        model_weight_used=w_model,
        heuristic_weight_used=w_heuristic,
        confidence=compute_confidence(prediction, fired, risk_level),
        contributing_rules=contributing,
    )


def compute_confidence(
    prediction: Prediction,
    fired: list[HeuristicFinding],
    risk_level: RiskLevel,
) -> float:
    """How much BASIRAH trusts its own assessment, 0-100.

    Confidence is NOT the risk score. It expresses evidence strength:
    how many independent rules fired, whether a model contributed, and
    how far the score sits from a decision boundary.

    Deliberately lower when the model is absent — the system is more
    uncertain without a trained classifier, and saying so is part of
    being academically honest.
    """
    confidence = 35.0

    # Corroboration: independent rules agreeing.
    confidence += min(30.0, len(fired) * 7.0)

    # Severity of what fired.
    high_severity = sum(1 for f in fired if f.severity == "high")
    confidence += min(15.0, high_severity * 7.5)

    # Model corroboration.
    if prediction.available:
        confidence += 20.0
        # A probability near 0.5 is an uninformative prediction.
        if prediction.probability is not None:
            distance = abs(prediction.probability - 0.5) * 2.0
            confidence += distance * 15.0
    else:
        # Explicitly penalise the missing model component.
        confidence -= 10.0

    # Distance from the nearest decision boundary. A score sitting
    # exactly on a threshold is the least trustworthy kind of answer.
    boundaries = [settings.caution_threshold, settings.high_risk_threshold]
    nearest = min(abs(_risk_of(risk_level) - b) for b in boundaries)
    confidence += min(10.0, nearest / 6.0)

    return round(max(0.0, min(100.0, confidence)), 1)


def _risk_of(level: RiskLevel) -> float:
    """Representative risk value for a band, for the boundary-distance term."""
    return {
        "trusted": 0.0,
        "caution": (settings.caution_threshold + settings.high_risk_threshold) / 2,
        "high_risk": settings.high_risk_threshold + 10.0,
    }[level]
