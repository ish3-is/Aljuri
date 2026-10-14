"""
Committee-safe image ensemble for BASIRAH.

The single most important property of this module is what it REFUSES
to say. It never converts "no synthetic indicators detected" into
"authentic". Authenticity is a claim that only cryptographically
verified provenance can support; everything here is advisory and is
named so that no downstream consumer can quietly upgrade it.

Decision hierarchy (highest authority first):

  1. verified provenance            -> PROVENANCE_VERIFIED
  2. both detectors agree synthetic -> LIKELY_SYNTHETIC
  3. both detectors agree real-side -> NO_STRONG_SYNTHETIC_INDICATORS
  4. detectors conflict             -> UNCERTAIN (abstain)
  5. out of distribution            -> UNCERTAIN (abstain)
  6. evidence quality too low       -> UNCERTAIN (limited reliability)

Note that step 3 deliberately does NOT yield an authenticity verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Assessment(str, Enum):
    """Outcome states. Names are deliberately not binary."""

    LIKELY_SYNTHETIC = "likely_synthetic"
    UNCERTAIN = "uncertain"
    NO_STRONG_SYNTHETIC_INDICATORS = "no_strong_synthetic_indicators"
    PROVENANCE_VERIFIED = "provenance_verified"
    PROVENANCE_UNAVAILABLE = "provenance_unavailable"


class Agreement(str, Enum):
    STRONG = "strong_agreement"
    MODERATE = "moderate_agreement"
    CONFLICT = "conflict"
    INSUFFICIENT = "insufficient"


class EvidenceQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Distribution(str, Enum):
    IN = "in_distribution"
    BORDERLINE = "borderline"
    OUT = "out_of_distribution"


# Below this, evidence quality forces abstention regardless of agreement.
_LOW_QUALITY_THRESHOLD = EvidenceQuality.LOW

# A detector sitting near 0.5 is not making a claim worth acting on.
# Measured on the held-out generator split; see results/phase37.
_MIN_DECISION_MARGIN = 0.30

# Only a genuinely decisive margin counts as strong agreement.
_STRONG_MARGIN = 0.45


@dataclass
class DetectorVote:
    name: str
    architecture: str
    synthetic_probability: float
    status: str = "available"
    limitations: list[str] = field(default_factory=list)
    unavailable_reason: str | None = None

    @property
    def available(self) -> bool:
        return self.unavailable_reason is None

    @property
    def margin(self) -> float:
        """Distance from a coin-flip. 0.5 -> 0.0, 0.0/1.0 -> 0.5."""
        return abs(self.synthetic_probability - 0.5)

    @property
    def side(self) -> str:
        return "synthetic" if self.synthetic_probability >= 0.5 else "authentic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelName": self.name,
            "architecture": self.architecture,
            "syntheticProbability": round(float(self.synthetic_probability), 6),
            "status": self.status if self.available else "unavailable",
            "unavailableReason": self.unavailable_reason,
            "limitations": list(self.limitations),
        }


@dataclass
class EnsembleOutcome:
    assessment: Assessment
    agreement: Agreement
    evidence_quality: EvidenceQuality
    distribution_status: Distribution
    synthetic_likelihood: float | None
    abstained: bool
    abstention_reasons: list[str]
    votes: list[DetectorVote]
    provenance_status: str
    authenticity_claim_supported: bool
    trust_assessment: float
    trust_components: dict[str, float]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment": self.assessment.value,
            "detectorAgreement": self.agreement.value,
            "evidenceQuality": self.evidence_quality.value,
            "distributionStatus": self.distribution_status.value,
            "syntheticLikelihood": None if self.synthetic_likelihood is None
            else round(float(self.synthetic_likelihood), 6),
            "abstained": self.abstained,
            "abstentionReasons": list(self.abstention_reasons),
            "detectors": [v.to_dict() for v in self.votes],
            "provenanceStatus": self.provenance_status,
            # The guard rail: this is only ever true with real
            # cryptographic provenance verification behind it.
            "authenticityClaimSupported": self.authenticity_claim_supported,
            "trustAssessment": round(float(self.trust_assessment), 2),
            "trustComponents": {k: round(float(v), 4) for k, v in self.trust_components.items()},
            "notes": list(self.notes),
        }


def classify_agreement(votes: list[DetectorVote]) -> Agreement:
    usable = [v for v in votes if v.available]
    if len(usable) < 2:
        return Agreement.INSUFFICIENT
    sides = {v.side for v in usable}
    if len(sides) > 1:
        return Agreement.CONFLICT
    margins = [v.margin for v in usable]
    if min(margins) >= _STRONG_MARGIN:
        return Agreement.STRONG
    if min(margins) >= _MIN_DECISION_MARGIN:
        return Agreement.MODERATE
    return Agreement.INSUFFICIENT


def assess_evidence_quality(
    *,
    width: int,
    height: int,
    warnings: list[str] | None = None,
) -> EvidenceQuality:
    """
    Evidence quality is computed from the IMAGE, never by nudging a
    model probability. It describes how much the pixels can support,
    independently of what any detector concluded.
    """
    warnings = warnings or []
    short_edge = min(width, height)
    if short_edge < 160 or any("low_resolution" in w for w in warnings):
        return EvidenceQuality.LOW
    if short_edge < 320 or any(
        w for w in warnings if "recompress" in w or "compression" in w or "resiz" in w
    ):
        return EvidenceQuality.MEDIUM
    return EvidenceQuality.HIGH


def decide(
    *,
    votes: list[DetectorVote],
    provenance_status: str,
    distribution_status: Distribution,
    evidence_quality: EvidenceQuality,
    url_risk: float | None = None,
    metadata_consistency: float | None = None,
) -> EnsembleOutcome:
    """
    Deterministic, explainable fusion. Every branch is recorded in
    `abstention_reasons` / `notes` so a committee can see why.
    """
    usable = [v for v in votes if v.available]
    agreement = classify_agreement(votes)
    reasons: list[str] = []
    notes: list[str] = []

    provenance_verified = provenance_status == "verified"

    # --- abstention gates -------------------------------------------------
    if agreement is Agreement.INSUFFICIENT:
        reasons.append("detector_evidence_insufficient")
    if agreement is Agreement.CONFLICT:
        reasons.append("detector_disagreement")
    if distribution_status is Distribution.OUT:
        reasons.append("out_of_distribution")
    if evidence_quality is _LOW_QUALITY_THRESHOLD:
        reasons.append("evidence_quality_low")

    abstained = bool(reasons)

    # --- assessment -------------------------------------------------------
    if provenance_verified:
        assessment = Assessment.PROVENANCE_VERIFIED
        notes.append("Cryptographically verified provenance is the only "
                     "basis for an authenticity claim.")
    elif abstained:
        assessment = Assessment.UNCERTAIN
    elif agreement in (Agreement.STRONG, Agreement.MODERATE):
        synthetic_side = sum(1 for v in usable if v.side == "synthetic")
        if synthetic_side == len(usable):
            assessment = Assessment.LIKELY_SYNTHETIC
        else:
            assessment = Assessment.NO_STRONG_SYNTHETIC_INDICATORS
            # The critical distinction, stated in the payload itself.
            notes.append(
                "No strong synthetic indicators detected. This is NOT a "
                "claim of authenticity; only verified provenance could "
                "support that."
            )
    else:
        assessment = Assessment.UNCERTAIN

    if provenance_status == "unavailable" and not provenance_verified:
        notes.append("Provenance could not be verified for this file, so "
                     "authenticity remains unestablished.")

    # --- synthetic likelihood --------------------------------------------
    # Averaging a DISAGREEING pair is actively harmful: 0.9 and 0.1
    # average to 0.5, which launders a total disagreement into a calm
    # mid-point and lets the conflict penalty be cancelled out. A
    # committee must not see that as reassurance. So when the
    # detectors conflict, no likelihood is published at all -- the
    # honest answer is "the detectors do not agree", not a midpoint.
    conflict = agreement is Agreement.CONFLICT
    if usable and not conflict:
        synth = sum(v.synthetic_probability for v in usable) / len(usable)
    elif usable:
        # Retained for transparency, but excluded from the trust maths.
        synth = sum(v.synthetic_probability for v in usable) / len(usable)
        conflict_mean = round(synth, 6)
    else:
        synth = None
        conflict_mean = None

    # --- trust assessment -------------------------------------------------
    # Deliberately NOT 1 - synthetic_probability. Provenance, agreement,
    # evidence quality and any URL risk all contribute, so the number
    # cannot be read as an authenticity probability.
    #
    # Sign convention: this value is TRUST, so evidence of SYNTHETIC
    # content must LOWER it. Adding the synthetic probability here was
    # an inversion that made a clearly fake image score as highly
    # trusted, which is the single worst failure this score can have.
    components: dict[str, float] = {}
    base = 50.0

    if conflict:
        # With disagreement the risk evidence is unknown, so it neither
        # raises nor lowers trust. Only the conflict penalty applies.
        components["risk_evidence"] = 0.0
        components["conflicting_detector_mean_not_used"] = conflict_mean or 0.0
    elif synth is not None:
        # Negative: more synthetic evidence -> less trust.
        components["risk_evidence"] = round(-synth * 40.0, 4)
        base += components["risk_evidence"]

    components["detector_agreement"] = {
        Agreement.STRONG: 8.0,
        Agreement.MODERATE: 3.0,
        Agreement.CONFLICT: -10.0,
        Agreement.INSUFFICIENT: -14.0,
    }[agreement]
    base += components["detector_agreement"]

    components["evidence_quality"] = {
        EvidenceQuality.HIGH: 6.0,
        EvidenceQuality.MEDIUM: 0.0,
        EvidenceQuality.LOW: -12.0,
    }[evidence_quality]
    base += components["evidence_quality"]

    components["distribution_familiarity"] = {
        Distribution.IN: 4.0,
        Distribution.BORDERLINE: -3.0,
        Distribution.OUT: -10.0,
    }[distribution_status]
    base += components["distribution_familiarity"]

    components["provenance"] = 14.0 if provenance_verified else (
        -6.0 if provenance_status == "unavailable" else 0.0
    )
    base += components["provenance"]

    if metadata_consistency is not None:
        # More internally consistent metadata -> slightly more trust.
        components["metadata_consistency"] = round((metadata_consistency - 0.5) * 8.0, 4)
        base += components["metadata_consistency"]

    if url_risk is not None:
        # URL risk is RISK, so it also lowers trust.
        components["url_risk"] = round(-url_risk * 20.0, 4)
        base += components["url_risk"]

    trust = max(0.0, min(100.0, base))

    return EnsembleOutcome(
        assessment=assessment,
        agreement=agreement,
        evidence_quality=evidence_quality,
        distribution_status=distribution_status,
        # On conflict the mean is withheld rather than published, so no
        # consumer downstream can mistake 0.5 for a neutral reading.
        synthetic_likelihood=None if conflict else synth,
        abstained=abstained,
        abstention_reasons=reasons,
        votes=votes,
        provenance_status=provenance_status,
        # Hard guard: authenticity requires real provenance verification.
        authenticity_claim_supported=provenance_verified,
        trust_assessment=trust,
        trust_components=components,
        notes=notes,
    )
