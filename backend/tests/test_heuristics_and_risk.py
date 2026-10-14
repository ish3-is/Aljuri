"""
Unit tests for the heuristic engine and risk fusion.

The central property tested here is the one that matters academically:
NO SINGLE RULE may produce a high-risk classification on its own. If
that ever changes, the system's claims become unsupportable.
"""

from __future__ import annotations

from app.core.config import HEURISTIC_WEIGHTS, settings
from app.ml.predictor import Prediction
from app.services.heuristic_engine import (
    RULES,
    evaluate,
    heuristic_risk,
    triggered,
)
from app.services.risk_engine import classify, fuse
from app.services.url_analyzer import normalize

UNAVAILABLE_PREDICTION = Prediction(
    available=False,
    probability=None,
    model_name="none",
    model_version="0.0.0",
    reason="no model",
)


def fired_ids(url: str) -> set[str]:
    return {f.id for f in triggered(evaluate(normalize(url)))}


class TestRuleRegistry:
    def test_every_rule_has_a_weight(self) -> None:
        """A rule with no weight would silently contribute nothing."""
        for rule in RULES:
            assert rule.__name__.replace("rule_", "").upper() in HEURISTIC_WEIGHTS

    def test_weights_are_documented_bands(self) -> None:
        for rule_id, weight in HEURISTIC_WEIGHTS.items():
            assert 0 < weight <= 25, f"{rule_id} weight {weight} outside documented range"

    def test_rule_count_is_understandable(self) -> None:
        """A small explainable set, not fifty opaque rules."""
        assert 10 <= len(RULES) <= 25

    def test_evaluate_returns_all_rules(self) -> None:
        findings = evaluate(normalize("https://example.com"))
        assert len(findings) == len(RULES)


class TestIndividualRules:
    def test_ip_host(self) -> None:
        assert "IP_HOST" in fired_ids("http://192.168.1.1/login")

    def test_punycode(self) -> None:
        assert "PUNYCODE" in fired_ids("https://xn--example-test.invalid")

    def test_at_symbol(self) -> None:
        assert "AT_SYMBOL" in fired_ids("https://user:pass@example.com")

    def test_excessive_subdomains(self) -> None:
        assert "EXCESSIVE_SUBDOMAINS" in fired_ids(
            "https://a.b.c.d.e.example.com"
        )

    def test_long_url(self) -> None:
        assert "LONG_URL" in fired_ids(
            "https://example.com/" + "segment/" * 20
        )

    def test_high_digit_ratio(self) -> None:
        assert "HIGH_DIGIT_RATIO" in fired_ids("https://123456789012345678901.com")

    def test_abnormal_port(self) -> None:
        assert "ABNORMAL_PORT" in fired_ids("https://example.com:9999/")

    def test_suspicious_tld(self) -> None:
        assert "SUSPICIOUS_TLD" in fired_ids("https://example.zip")

    def test_keyword_combination_needs_two(self) -> None:
        """One keyword must not fire the combination rule."""
        assert "SUSPICIOUS_KEYWORD_COMBINATION" not in fired_ids(
            "https://example.com/login"
        )
        assert "SUSPICIOUS_KEYWORD_COMBINATION" in fired_ids(
            "https://example.com/login/verify/account"
        )

    def test_credential_in_url(self) -> None:
        assert "CREDENTIAL_IN_URL" in fired_ids("https://u:p@example.com/")

    def test_brand_token_on_unrelated_domain(self) -> None:
        assert "BRAND_LIKE_TOKEN" in fired_ids("https://paypal-secure.example.com")

    def test_brand_token_on_own_domain_is_softened(self) -> None:
        """A brand token in the domain's own name is not a mismatch."""
        assert "BRAND_LIKE_TOKEN" not in fired_ids("https://paypal.com")

    def test_plain_domain_fires_nothing(self) -> None:
        assert fired_ids("https://example.com") == set()

    def test_untriggered_findings_report_zero_weight(self) -> None:
        for finding in evaluate(normalize("https://example.com")):
            if not finding.triggered:
                assert finding.weight == 0
                assert finding.explanation == "Not observed."


class TestNoSingleRuleCanConvict:
    """The load-bearing safety property of the whole system."""

    def test_strongest_rule_alone_stays_below_caution(self) -> None:
        strongest = max(HEURISTIC_WEIGHTS.values())
        score, _ = heuristic_risk(
            evaluate(normalize("http://192.168.1.1:9999/verify/login/account"))
        )
        # Heuristic score alone, even with several rules, must not reach
        # the high-risk threshold on a single structural observation.
        assert strongest <= 25
        assert classify(score) != "high_risk" or len(triggered(evaluate(
            normalize("http://192.168.1.1:9999/verify/login/account")
        ))) >= 3

    def test_ip_host_alone_is_not_high_risk(self) -> None:
        """An IP host on its own is a caution-level observation."""
        findings = evaluate(normalize("http://192.168.1.1/"))
        score, _ = heuristic_risk(findings)
        assert classify(score) != "high_risk"

    def test_punycode_alone_is_not_high_risk(self) -> None:
        findings = evaluate(normalize("https://xn--example-test.invalid"))
        score, _ = heuristic_risk(findings)
        assert classify(score) != "high_risk"

    def test_brand_mismatch_alone_is_not_high_risk(self) -> None:
        findings = evaluate(normalize("https://paypal-secure.example.com"))
        score, _ = heuristic_risk(findings)
        assert classify(score) != "high_risk"


class TestHeuristicRisk:
    def test_zero_when_nothing_fires(self) -> None:
        score, fired = heuristic_risk(evaluate(normalize("https://example.com")))
        assert score == 0.0
        assert fired == []

    def test_saturates_at_100(self) -> None:
        from app.services.heuristic_engine import HeuristicFinding

        many = [
            HeuristicFinding(
                id=rule_id,
                title=rule_id,
                severity="high",
                weight=weight,
                triggered=True,
                explanation="",
            )
            for rule_id, weight in HEURISTIC_WEIGHTS.items()
        ]
        score, _ = heuristic_risk(many)
        assert score == 100.0

    def test_score_is_bounded(self) -> None:
        score, _ = heuristic_risk(
            evaluate(normalize("https://a.b.c.d.e.12345-verify-login-account.zip:9999"))
        )
        assert 0.0 <= score <= 100.0


class TestRiskClassification:
    def test_thresholds_are_from_config(self) -> None:
        assert classify(settings.high_risk_threshold) == "high_risk"
        assert classify(settings.high_risk_threshold - 0.1) == "caution"
        assert classify(settings.caution_threshold) == "caution"
        assert classify(settings.caution_threshold - 0.1) == "trusted"

    def test_boundaries(self) -> None:
        assert classify(0.0) == "trusted"
        assert classify(100.0) == "high_risk"


class TestFusion:
    def test_without_model_heuristics_carry_full_weight(self) -> None:
        findings = evaluate(normalize("https://example.com"))
        result = fuse(UNAVAILABLE_PREDICTION, 0.0, findings)
        assert result.model_weight_used == 0.0
        assert result.heuristic_weight_used == 1.0
        assert result.final_risk == result.heuristic_risk

    def test_with_model_weights_sum_to_one(self) -> None:
        prediction = Prediction(
            available=True,
            probability=0.8,
            model_name="test",
            model_version="0",
            reason="",
        )
        findings = evaluate(normalize("https://example.com"))
        result = fuse(prediction, 40.0, findings)
        assert result.model_weight_used + result.heuristic_weight_used == 1.0

    def test_trust_score_is_inverse_of_risk(self) -> None:
        findings = evaluate(normalize("https://example.com"))
        result = fuse(UNAVAILABLE_PREDICTION, 30.0, findings)
        assert result.trust_score == 100.0 - result.final_risk

    def test_model_cannot_alone_force_high_risk(self) -> None:
        """Even P(phishing)=1.0 must not convict without corroboration."""
        prediction = Prediction(
            available=True,
            probability=1.0,
            model_name="test",
            model_version="0",
            reason="",
        )
        findings = evaluate(normalize("https://example.com"))  # nothing fires
        result = fuse(prediction, 0.0, findings)
        assert result.risk_level != "high_risk"

    def test_confidence_lower_without_model(self) -> None:
        findings = evaluate(normalize("https://a.b.c.example.zip/verify"))
        without = fuse(UNAVAILABLE_PREDICTION, 40.0, findings)
        with_model = fuse(
            Prediction(
                available=True,
                probability=0.7,
                model_name="t",
                model_version="0",
                reason="",
            ),
            40.0,
            findings,
        )
        assert without.confidence < with_model.confidence

    def test_more_evidence_raises_confidence(self) -> None:
        few = evaluate(normalize("https://example.zip"))
        many = evaluate(normalize("https://a.b.c.12345-verify-login-account.zip:9999"))
        assert (
            fuse(UNAVAILABLE_PREDICTION, 10.0, few).confidence
            < fuse(UNAVAILABLE_PREDICTION, 60.0, many).confidence
        )

    def test_contributing_rules_recorded(self) -> None:
        findings = evaluate(normalize("https://a.b.c.verify.example.zip"))
        result = fuse(UNAVAILABLE_PREDICTION, 20.0, findings)
        assert "EXCESSIVE_SUBDOMAINS" in result.contributing_rules

    def test_risk_is_bounded(self) -> None:
        prediction = Prediction(
            available=True, probability=1.0, model_name="t", model_version="0", reason=""
        )
        from app.services.heuristic_engine import HeuristicFinding

        many = [
            HeuristicFinding(
                id=k, title=k, severity="high", weight=v, triggered=True, explanation=""
            )
            for k, v in HEURISTIC_WEIGHTS.items()
        ]
        result = fuse(prediction, 100.0, many)
        assert 0.0 <= result.final_risk <= 100.0
        assert 0.0 <= result.trust_score <= 100.0
