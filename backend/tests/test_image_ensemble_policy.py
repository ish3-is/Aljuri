"""
Tests for the committee-safe ensemble policy.

The tests that matter most are the negative ones: they assert that the
system CANNOT produce an authenticity claim without provenance, and
that it abstains under the conditions the brief requires.
"""

from __future__ import annotations

import pytest

from app.image.ensemble.policy import (
    Agreement,
    Assessment,
    Distribution,
    DetectorVote,
    EvidenceQuality,
    assess_evidence_quality,
    classify_agreement,
    decide,
)


def vote(name: str, p: float) -> DetectorVote:
    return DetectorVote(
        name=name,
        architecture="test",
        synthetic_probability=p,
    )


def unavailable(name: str) -> DetectorVote:
    return DetectorVote(
        name=name,
        architecture="test",
        synthetic_probability=0.5,
        unavailable_reason="model not present",
    )


class TestAgreement:
    def test_identical_confident_votes_are_strong(self):
        assert classify_agreement([vote("a", 0.99), vote("b", 0.97)]) is Agreement.STRONG

    def test_opposite_sides_are_conflict(self):
        assert classify_agreement([vote("a", 0.95), vote("b", 0.05)]) is Agreement.CONFLICT

    def test_near_half_is_insufficient(self):
        assert classify_agreement([vote("a", 0.52), vote("b", 0.51)]) is Agreement.INSUFFICIENT

    def test_single_detector_is_insufficient(self):
        assert classify_agreement([vote("a", 0.99)]) is Agreement.INSUFFICIENT

    def test_unavailable_detector_does_not_count_as_a_second_opinion(self):
        assert classify_agreement([vote("a", 0.99), unavailable("b")]) is Agreement.INSUFFICIENT


class TestEvidenceQuality:
    def test_tiny_image_is_low(self):
        assert assess_evidence_quality(width=96, height=96) is EvidenceQuality.LOW

    def test_small_image_is_medium(self):
        assert assess_evidence_quality(width=256, height=256) is EvidenceQuality.MEDIUM

    def test_large_image_is_high(self):
        assert assess_evidence_quality(width=1024, height=1024) is EvidenceQuality.HIGH

    def test_low_resolution_warning_forces_low(self):
        assert assess_evidence_quality(
            width=1024, height=1024, warnings=["low_resolution"]
        ) is EvidenceQuality.LOW


class TestDecisionHierarchy:
    def test_verified_provenance_is_the_only_authenticity_claim(self):
        out = decide(
            votes=[vote("a", 0.02), vote("b", 0.03)],
            provenance_status="verified",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.PROVENANCE_VERIFIED
        assert out.authenticity_claim_supported is True

    def test_agreement_on_synthetic_side(self):
        out = decide(
            votes=[vote("a", 0.97), vote("b", 0.95)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.LIKELY_SYNTHETIC

    def test_agreement_on_real_side_is_not_an_authenticity_claim(self):
        """
        The central requirement: agreeing that an image looks real must
        never be reported as verified authenticity.
        """
        out = decide(
            votes=[vote("a", 0.02), vote("b", 0.04)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.NO_STRONG_SYNTHETIC_INDICATORS
        assert out.authenticity_claim_supported is False
        assert any("NOT a claim of authenticity" in n for n in out.notes)

    def test_disagreement_abstains(self):
        out = decide(
            votes=[vote("a", 0.95), vote("b", 0.05)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.UNCERTAIN
        assert out.abstained is True
        assert "detector_disagreement" in out.abstention_reasons

    def test_ood_abstains(self):
        out = decide(
            votes=[vote("a", 0.98), vote("b", 0.97)],
            provenance_status="unavailable",
            distribution_status=Distribution.OUT,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.UNCERTAIN
        assert "out_of_distribution" in out.abstention_reasons

    def test_low_quality_abstains(self):
        out = decide(
            votes=[vote("a", 0.98), vote("b", 0.97)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.LOW,
        )
        assert out.assessment is Assessment.UNCERTAIN
        assert "evidence_quality_low" in out.abstention_reasons

    def test_borderline_ood_alone_does_not_abstain(self):
        out = decide(
            votes=[vote("a", 0.98), vote("b", 0.97)],
            provenance_status="unavailable",
            distribution_status=Distribution.BORDERLINE,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.LIKELY_SYNTHETIC

    def test_unavailable_detector_forces_insufficient(self):
        out = decide(
            votes=[vote("a", 0.99), unavailable("b")],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.UNCERTAIN
        assert "detector_evidence_insufficient" in out.abstention_reasons


class TestTrustSemantics:
    def test_trust_is_not_one_minus_synthetic_probability(self):
        """
        Two inputs with the same synthetic likelihood but different
        provenance must produce different trust. If trust were simply
        1 - p, these would be equal.
        """
        base = dict(
            votes=[vote("a", 0.4), vote("b", 0.4)],
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        with_prov = decide(provenance_status="verified", **base)
        without = decide(provenance_status="unavailable", **base)
        assert with_prov.trust_assessment != without.trust_assessment

    def test_conflict_is_never_reassuring(self):
        """
        Conflict must not read as comfort.

        Two detectors at 0.9 and 0.1 average to 0.5. Publishing that
        mean -- and then applying a conflict penalty on top -- produced
        a trust number that looked like a mild risk finding rather than
        "we do not know". The mean is withheld entirely.

        Note the deliberate asymmetry: conflict scores HIGHER than
        "both detectors strongly synthetic", because that case really
        does have strong evidence of a fake image. Unknown is not the
        same as known-bad.
        """
        conflict = decide(
            votes=[vote("a", 0.9), vote("b", 0.1)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        both_synthetic = decide(
            votes=[vote("a", 0.9), vote("b", 0.95)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert conflict.assessment is Assessment.UNCERTAIN
        assert conflict.abstained is True
        # The laundering midpoint is never published.
        assert conflict.synthetic_likelihood is None
        assert conflict.trust_assessment > both_synthetic.trust_assessment
        assert "detector_disagreement" in conflict.abstention_reasons

    def test_conflict_publishes_no_likelihood_in_payload(self):
        payload = decide(
            votes=[vote("a", 0.95), vote("b", 0.05)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        ).to_dict()
        assert payload["syntheticLikelihood"] is None
        assert payload["assessment"] == "uncertain"

    def test_trust_is_clamped_to_range(self):
        for prov in ("verified", "unavailable", "present_unverified"):
            out = decide(
                votes=[vote("a", 0.0), vote("b", 0.0)],
                provenance_status=prov,
                distribution_status=Distribution.IN,
                evidence_quality=EvidenceQuality.HIGH,
            )
            assert 0.0 <= out.trust_assessment <= 100.0

    def test_url_risk_is_a_separate_component(self):
        out = decide(
            votes=[vote("a", 0.5), vote("b", 0.5)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.MEDIUM,
            url_risk=0.9,
        )
        assert "url_risk" in out.trust_components
        assert out.trust_components["url_risk"] < 0


class TestTrustDirection:
    """
    Regression tests for a real defect found in end-to-end testing:
    evidence of SYNTHETIC content was ADDING to trust, so a clearly
    fake image scored as highly trusted. Unit tests missed it because
    they only checked ordering, never the sign of the risk component.
    """

    def test_synthetic_evidence_lowers_trust(self):
        risky = decide(
            votes=[vote("a", 0.95), vote("b", 0.95)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        clean = decide(
            votes=[vote("a", 0.02), vote("b", 0.02)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert risky.trust_assessment < clean.trust_assessment, (
            f"synthetic={risky.trust_assessment} should be BELOW "
            f"real-side={clean.trust_assessment}"
        )

    def test_risk_component_is_negative(self):
        out = decide(
            votes=[vote("a", 0.9), vote("b", 0.9)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.trust_components["risk_evidence"] < 0

    def test_url_risk_lowers_trust(self):
        low = decide(
            votes=[vote("a", 0.5), vote("b", 0.5)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.MEDIUM,
            url_risk=0.1,
        )
        high = decide(
            votes=[vote("a", 0.5), vote("b", 0.5)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.MEDIUM,
            url_risk=0.95,
        )
        assert high.trust_assessment < low.trust_assessment

    def test_likely_synthetic_never_earns_high_trust(self):
        out = decide(
            votes=[vote("a", 0.99), vote("b", 0.98)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        assert out.assessment is Assessment.LIKELY_SYNTHETIC
        assert out.trust_assessment < 50.0


class TestSerialisation:
    @pytest.mark.parametrize("agreement,expected", [
        (Agreement.STRONG, "strong_agreement"),
        (Agreement.CONFLICT, "conflict"),
        (Agreement.INSUFFICIENT, "insufficient"),
    ])
    def test_agreement_serialises_to_stable_strings(self, agreement, expected):
        assert agreement.value == expected

    def test_payload_exposes_no_authentic_claim_without_provenance(self):
        out = decide(
            votes=[vote("a", 0.01), vote("b", 0.01)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        payload = out.to_dict()
        assert payload["authenticityClaimSupported"] is False
        assert payload["assessment"] == "no_strong_synthetic_indicators"

    def test_payload_is_json_safe(self):
        import json
        out = decide(
            votes=[vote("a", 0.9), vote("b", 0.9)],
            provenance_status="unavailable",
            distribution_status=Distribution.IN,
            evidence_quality=EvidenceQuality.HIGH,
        )
        json.dumps(out.to_dict())
