"""
Image risk engine.

Fuses four independent evidence channels into one trust score, under
three constraints learned from the URL phases:

1. **The model is primary.** Synthetic likelihood carries the decision.
   Metadata, forensics and provenance are corroborating context.

2. **Weak channels cannot manufacture confidence.** Every metadata and
   forensic signal is weighted ``weak``. They may nudge the score within a
   bounded band; they cannot flip an assessment on their own. This is the
   direct fix for the URL fusion failure, where OR-combining heuristics
   bought 4 points of recall for 36 points of false-positive rate.

3. **Fusion is measured, not assumed.** `FUSION_MAX_NUDGE` is a small
   constant precisely so that any future claim that fusion "helps" has to
   be demonstrated against this baseline rather than assumed.

There is deliberately **no** rule of the form "absent EXIF => synthetic".
Such a rule would fire on every screenshot and every social-media image.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.image.forensics import ForensicReport
from app.image.metadata import MetadataResult
from app.image.provenance import ProvenanceResult, ProvenanceStatus
from app.image.schemas import Assessment

#: Maximum total score movement attributable to non-model channels.
FUSION_MAX_NUDGE = 4.0

#: Probabilities inside this band are reported as uncertain, not guessed.
UNCERTAIN_LOW = 0.35
UNCERTAIN_HIGH = 0.65


@dataclass
class RiskAssessment:
    trust_score: float
    risk_level: str
    confidence: float
    assessment: Assessment
    uncertain: bool
    #: How much the non-model channels moved the score, and why.
    fusion_nudge: float
    fusion_reasons: list[str] = field(default_factory=list)
    channels: list[dict[str, Any]] = field(default_factory=list)


def _risk_level(score: float) -> str:
    if score >= 75:
        return "low_risk"
    if score >= 50:
        return "caution"
    if score >= 25:
        return "elevated"
    return "high_risk"


def classify(probability: float | None) -> tuple[Assessment, bool]:
    """Map a probability to a three-way assessment. Never binary."""
    if probability is None:
        return Assessment.UNCERTAIN, True
    if UNCERTAIN_LOW < probability < UNCERTAIN_HIGH:
        return Assessment.UNCERTAIN, True
    if probability >= UNCERTAIN_HIGH:
        return Assessment.LIKELY_SYNTHETIC, False
    return Assessment.LIKELY_AUTHENTIC, False


def assess(
    *,
    synthetic_probability: float | None,
    metadata: MetadataResult | None,
    forensics: ForensicReport | None,
    provenance: ProvenanceResult | None,
) -> RiskAssessment:
    """Fuse evidence into a trust score with bounded non-model influence."""
    assessment, uncertain = classify(synthetic_probability)

    if synthetic_probability is None:
        # No model. Do not substitute a confident-looking default; an
        # honest "cannot tell" is more useful than a fabricated number.
        base_trust = 50.0
        confidence = 0.0
        reasons = ["no synthetic-media model available; score reflects no model evidence"]
    else:
        base_trust = (1.0 - synthetic_probability) * 100.0
        # Confidence is deliberately NOT the probability. A model that
        # says 0.51 is not 51% confident - it is undecided.
        distance_from_boundary = abs(synthetic_probability - 0.5) * 2.0
        confidence = round(min(100.0, distance_from_boundary * 100.0), 1)
        reasons = []

    # --- bounded corroboration -------------------------------------
    nudge = 0.0
    channels: list[dict[str, Any]] = []

    if metadata is not None:
        channels.append({
            "name": "metadata",
            "summary": metadata.exif_interpretation,
            "weight": "weak",
        })
        # Camera EXIF nudges *toward* authentic, and only weakly. It never
        # proves authenticity: software writes EXIF too.
        if metadata.camera_make or metadata.camera_model:
            nudge += 1.0
            reasons.append("camera EXIF present (weak support for authenticity)")

    if provenance is not None:
        channels.append({
            "name": "provenance",
            "summary": provenance.limitation or provenance.status.value,
            "weight": "weak",
        })
        if provenance.status is ProvenanceStatus.VERIFIED:
            nudge += FUSION_MAX_NUDGE * 0.5
            reasons.append("provenance cryptographically verified")

    if forensics is not None:
        channels.append({
            "name": "forensics",
            "summary": (
                f"{len([s for s in forensics.signals if s.value is not None])} "
                "measurable forensic signals; all corroborating only"
            ),
            "weight": "weak",
        })

    # Clamp the total so weak channels can never dominate.
    if nudge > FUSION_MAX_NUDGE:
        reasons.append(f"fusion nudge capped at {FUSION_MAX_NUDGE}")
        nudge = FUSION_MAX_NUDGE
    nudge = max(0.0, nudge)

    final_trust = max(0.0, min(100.0, base_trust + nudge))

    return RiskAssessment(
        trust_score=round(final_trust, 1),
        risk_level=_risk_level(final_trust),
        confidence=confidence,
        assessment=assessment,
        uncertain=uncertain,
        fusion_nudge=round(nudge, 2),
        fusion_reasons=reasons,
        channels=channels,
    )
