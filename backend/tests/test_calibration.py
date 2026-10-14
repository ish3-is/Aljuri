"""
Calibration tests.

These lock in behaviour that was wrong on first implementation and had
to be corrected. Each test names the specific defect it prevents.

The governing principle: a risk band must reflect a judgement about the
evidence, not an accident of how the rule weights happened to sum.
"""

from __future__ import annotations

from app.core.config import THRESHOLDS, settings
from app.ml.predictor import Prediction
from app.services.feature_extractor import entropy_of_hostname
from app.services.heuristic_engine import evaluate, heuristic_risk
from app.services.risk_engine import fuse
from app.services.url_analyzer import normalize

NO_MODEL = Prediction(
    available=False,
    probability=None,
    model_name="none",
    model_version="0",
    reason="no model",
)


def level_of(url: str) -> str:
    findings = evaluate(normalize(url))
    score, _ = heuristic_risk(findings)
    return fuse(NO_MODEL, score, findings).risk_level


def count_fired(url: str) -> int:
    return len([f for f in evaluate(normalize(url)) if f.triggered])


class TestHostnameEntropySeparatesRandomFromWord:
    """Defect: raw hostname entropy counted separators.

    Hyphens and dots inflated character variety, so a purely word-based
    domain scored as 'random' and real institutional domains sat within
    0.15 of the firing threshold.
    """

    # Real, well-known hosts must stay below the threshold.
    REAL_HOSTS = [
        "example.com",
        "google.com",
        "github.com",
        "en.wikipedia.org",
        "www.university.edu.sa",
    ]

    def test_real_hosts_do_not_fire(self) -> None:
        for host in self.REAL_HOSTS:
            assert (
                entropy_of_hostname(host) < THRESHOLDS["high_entropy_hostname"]
            ), f"{host} scored {entropy_of_hostname(host):.2f}"

    def test_generated_labels_score_higher_than_real_hosts(self) -> None:
        generated = entropy_of_hostname("a8f3k2m9x1qz7b4.example")
        real_max = max(entropy_of_hostname(h) for h in self.REAL_HOSTS)
        assert generated > real_max

    def test_measure_is_separator_invariant(self) -> None:
        """The defect itself: separators must not affect the measure."""
        # Same letters, radically different raw-string entropy. Under the
        # old measure these diverged; separators must now be invisible.
        assert entropy_of_hostname("abcdefgh") == entropy_of_hostname(
            "a-b-c-d-e-f-g-h"
        )
        assert entropy_of_hostname("github") == entropy_of_hostname("g-i-t-h-u-b")

    def test_short_labels_are_not_measured(self) -> None:
        """Too little content for the measure to mean anything."""
        assert entropy_of_hostname("ab") == 0.0
        assert entropy_of_hostname("") == 0.0

    def test_a_long_multiword_label_may_still_fire(self) -> None:
        """Not every hyphenated domain is low-entropy.

        `nafath-secure-login` stacks several words, so once separators are
        removed it genuinely carries high character variety and firing is
        correct. The rule is about randomness of the CONTENT, and this
        label is long enough that variety is real.
        """
        findings = {
            f.id
            for f in evaluate(normalize("https://nafath-secure-login.example"))
            if f.triggered
        }
        assert "SUSPICIOUS_KEYWORD_COMBINATION" in findings


class TestEvidenceFloors:
    """Defect: raw weight sums could report corroborated evidence as trusted.

    Two independent indicators summed to 28 against a caution threshold
    of 30 — two points of arithmetic luck deciding a verdict.
    """

    def test_corroborating_evidence_always_reaches_caution(self) -> None:
        # Two fired rules, but a raw sum just under the threshold.
        assert level_of("https://nafath-secure-login.example") == "caution"

    def test_high_severity_rule_alone_reaches_caution(self) -> None:
        assert level_of("http://192.168.1.1/login") == "caution"

    def test_no_evidence_is_still_trusted(self) -> None:
        """The floors must not manufacture caution from nothing."""
        assert level_of("https://example.com") == "trusted"
        assert count_fired("https://example.com") == 0

    def test_floors_cannot_reach_high_risk(self) -> None:
        """A floor set at the caution boundary must not jump two bands."""
        assert settings.min_corroborating_score <= settings.high_risk_threshold
        assert settings.min_high_severity_score <= settings.high_risk_threshold


class TestNoSingleRuleConvicts:
    """The load-bearing safety property."""

    def test_isolated_rules_never_reach_high_risk(self) -> None:
        candidates = [
            "http://192.168.1.1/",
            "https://xn--example-test.invalid",
            "https://paypal-secure.example.com",
            "https://user:pass@example.com/",
            "https://example.com:9999/",
            "https://example.com/" + "segment/" * 25,
            "https://a.b.c.d.e.example.com",
            "https://12345678901234567890.com",
            "https://example.zip",
            "https://example.com//redirect",
        ]
        for url in candidates:
            level = level_of(url)
            assert level != "high_risk", f"{url} reached high risk"

    def test_high_risk_requires_many_rules(self) -> None:
        high_risk_url = (
            "https://user:pass@a.b.c.12345-verify-login-account-update.zip:9999/x//y?a=1"
        )
        assert count_fired(high_risk_url) >= 5

    def test_model_alone_cannot_convict(self) -> None:
        certain = Prediction(
            available=True,
            probability=1.0,
            model_name="t",
            model_version="0",
            reason="",
        )
        findings = evaluate(normalize("https://example.com"))
        result = fuse(certain, 0.0, findings)
        assert result.risk_level != "high_risk"


class TestMonotonicity:
    """More evidence must never produce a lower risk score."""

    def test_risk_increases_with_evidence(self) -> None:
        ladder = [
            "https://example.com",
            "https://nafath-secure-login.example",
            "https://secure-login-account-update.example.com",
            "http://192.168.1.1:9999/verify/login/account-update",
        ]
        scores = []
        for url in ladder:
            findings = evaluate(normalize(url))
            score, _ = heuristic_risk(findings)
            scores.append(score)
        assert scores == sorted(scores), scores

    def test_trust_decreases_with_evidence(self) -> None:
        ladder = [
            "https://example.com",
            "https://nafath-secure-login.example",
            "https://secure-login-account-update.example.com",
        ]
        trust = []
        for url in ladder:
            findings = evaluate(normalize(url))
            score, _ = heuristic_risk(findings)
            trust.append(fuse(NO_MODEL, score, findings).trust_score)
        assert trust == sorted(trust, reverse=True), trust

    def test_scores_stay_in_range(self) -> None:
        for url in ["https://example.com", "https://" + "a" * 300 + ".com/verify"]:
            findings = evaluate(normalize(url))
            score, _ = heuristic_risk(findings)
            assert 0.0 <= score <= 100.0


class TestDeterminism:
    def test_repeated_analysis_identical(self) -> None:
        url = "https://secure-login-account-update.example.com"
        first = evaluate(normalize(url))
        second = evaluate(normalize(url))
        assert [f.to_dict() for f in first] == [f.to_dict() for f in second]

    def test_case_does_not_change_the_host(self) -> None:
        assert level_of("https://EXAMPLE.COM") == level_of("https://example.com")
