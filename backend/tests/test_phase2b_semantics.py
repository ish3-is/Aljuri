"""
Semantic correctness tests — label orientation and prediction sanity.

These exist because Phase 2B trained an entire model on INVERTED
PhiUSIIL labels before it was caught. The resulting model scored
google.com at 99.9% phishing and the actual phishing URLs at 0%: a
confidently inverted detector, which is worse than no detector.

Nothing in the metric suite would have revealed this. Every AUC, F1 and
accuracy figure was computed against the same inverted labels, so the
model looked excellent. These tests assert on MEANING instead of on
numbers.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.ml.datasets import (
    LabelOrientationError,
    detect_label_orientation,
)
from app.services.url_analyzer import normalize

BACKEND = Path(__file__).resolve().parents[1]


# ====================================================================
# LABEL ORIENTATION
# ====================================================================


class TestLabelOrientation:
    def test_textual_tokens_are_unambiguous(self) -> None:
        assert detect_label_orientation(["phishing"] * 10) == 1
        assert detect_label_orientation(["benign"] * 10) == -1

    def test_numeric_data_is_ambiguous(self) -> None:
        """A bare 0/1 column cannot reveal which is which.

        Returning 1 here is what caused the Phase 2B inversion.
        """
        assert detect_label_orientation(["1"] * 50 + ["0"] * 50) == 0

    def test_numeric_never_guesses(self) -> None:
        assert detect_label_orientation(["1", "0", "1", "0"]) == 0

    def test_empty_is_ambiguous(self) -> None:
        assert detect_label_orientation([]) == 0

    def test_audit_refuses_unstated_numeric_orientation(self, tmp_path: Path) -> None:
        """The audit must abort rather than assume the convention."""
        from app.ml.datasets import audit_csv

        path = tmp_path / "numeric.csv"
        path.write_text(
            "url,label\nhttps://a.example,1\nhttps://b.example,0\n", encoding="utf-8"
        )
        with pytest.raises(LabelOrientationError):
            audit_csv(path, name="t", source_url="x", source_label="t")

    def test_audit_accepts_explicit_orientation(self, tmp_path: Path) -> None:
        from app.ml.datasets import PHISHING, audit_csv

        path = tmp_path / "numeric.csv"
        path.write_text(
            "url,label\nhttps://a.example,1\nhttps://b.example,0\n", encoding="utf-8"
        )
        result = audit_csv(
            path,
            name="t",
            source_url="x",
            source_label="t",
            label_orientation=-1,
        )
        # label 1 = legitimate in the file, so after flipping it must be 0.
        by_url = {r.url: r.label for r in result.rows}
        assert by_url["https://a.example"] != PHISHING
        assert by_url["https://b.example"] == PHISHING


# ====================================================================
# PHIUSIIL SPECIFIC — the corpus that caused the failure
# ====================================================================


class TestPhiusilOrientation:
    """PhiUSIIL: label 1 = legitimate, label 0 = phishing.

    Asserted against the SOURCE file, not the processed output, so the
    test tracks the real encoding.
    """

    @pytest.fixture(scope="class")
    def raw(self) -> Path:
        path = BACKEND / "datasets" / "raw" / "phiusil_raw.csv"
        if not path.exists():
            pytest.skip("raw PhiUSIIL not present")
        return path

    def test_source_encoding_is_legitimate_one(self, raw: Path) -> None:
        """A sanity check on the corpus itself.

        Label 1 should be the larger, legitimate-looking class (134,850
        rows), label 0 the phishing class (100,945). If this ever flips,
        the dataset on disk is not the one documented.
        """
        counts = {"0": 0, "1": 0}
        with raw.open("r", encoding="utf-8-sig", newline="") as handle:
            for record in csv.DictReader(handle):
                counts[record["label"]] += 1
        assert counts["1"] > counts["0"], (
            "PhiUSIIL label 1 (legitimate) should outnumber label 0 "
            f"(phishing); got {counts}"
        )

    def test_processed_labels_are_flipped_to_phishing_one(self) -> None:
        """The processed corpus must use 1 = phishing."""
        path = BACKEND / "datasets" / "processed" / "phiusil_clean.csv"
        if not path.exists():
            pytest.skip("processed dataset not built")
        # Known-legitimate organisations must be label 0 (not phishing).
        legitimate_markers = ("uni-mainz.de", "rewildingargentina.org")
        found: dict[str, str] = {}
        with path.open("r", encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                for marker in legitimate_markers:
                    if marker in record["url"] and marker not in found:
                        found[marker] = record["label"]
        for marker in legitimate_markers:
            if marker in found:
                assert found[marker] == "0", (
                    f"{marker} is a real institution and must not be "
                    f"labelled phishing; got {found[marker]}"
                )


# ====================================================================
# PREDICTION SEMANTICS
# ====================================================================


class TestPredictionSemantics:
    """Assert what the model MEANS, not what it scores.

    These are the checks that would have caught the inverted model.
    """

    @pytest.fixture(scope="class")
    def predictor(self):
        from app.ml.production import predict_risk_production

        class _P:
            @staticmethod
            def p(url: str):
                return predict_risk_production(normalize(url)).probability

        return _P

    def test_known_legitimate_hosts_are_not_flagged(self, predictor) -> None:
        """A model that calls google.com phishing is broken.

        Deliberately not an accuracy assertion: it is a meaning
        assertion. Tolerates an unavailable model.

        NOTE: this deliberately tests only BARE-DOMAIN legitimate hosts.
        See test_phiusil_path_artifact_is_a_known_defect for why
        legitimate URLs *with paths* are known to be misclassified, and
        why including them here would encode the corpus artifact as a
        requirement.
        """
        legitimate = [
            "https://www.google.com",
            "https://www.wikipedia.org",
            "https://www.university.edu.sa",
            "https://www.nasa.gov",
            "https://news.ycombinator.com",
        ]
        for url in legitimate:
            probability = predictor.p(url)
            if probability is None:
                pytest.skip("no model loaded")
            assert probability < 0.5, (
                f"{url} scored {probability:.2f} phishing. A production "
                f"detector must not flag these."
            )

    def test_corpus_shaped_legitimate_urls_are_not_flagged(self, predictor) -> None:
        """Domains drawn from PhiUSIIL's legitimate class.

        These match the shapes the model was trained on, so they test
        that the model behaves correctly within its own distribution.
        """
        for url in (
            "https://www.teramill.com",
            "https://www.uni-mainz.de",
            "https://www.rewildingargentina.org",
        ):
            probability = predictor.p(url)
            if probability is None:
                pytest.skip("no model loaded")
            assert probability < 0.5, f"{url} scored {probability:.2f}"

    def test_known_phishing_patterns_are_flagged(self, predictor) -> None:
        """Structurally blatant phishing must score high.

        These are the shapes a phishing detector exists to catch.
        """
        phishing = [
            "https://secure-login-account-update.example.com",
            "https://verify-account-billing-now.example.net/reset",
            "http://www.f0519141.xsph.ru",
        ]
        for url in phishing:
            probability = predictor.p(url)
            if probability is None:
                pytest.skip("no model loaded")
            assert probability > 0.5, (
                f"{url} scored only {probability:.2f}; blatant phishing "
                f"patterns must score high."
            )

    def test_probability_is_oriented_correctly(self, predictor) -> None:
        """The decisive inversion check.

        If the model were inverted, legitimate hosts would score ABOVE
        blatant phishing. Compare them directly.
        """
        legitimate = predictor.p("https://www.google.com")
        phishing = predictor.p("https://secure-login-account-update.example.com")
        if legitimate is None or phishing is None:
            pytest.skip("no model loaded")
        assert phishing > legitimate, (
            f"phishing ({phishing:.2f}) must score above legitimate "
            f"({legitimate:.2f}); the model appears inverted."
        )


class TestPhiusilPathArtifactIsAKnownDefect:
    """PhiUSIIL's legitimate class contains ZERO URLs with a path.

    Measured from the raw corpus: 0 of 134,850 legitimate rows have a
    non-empty path, versus 27.2% of phishing rows. "Carries a path" is
    therefore close to a perfect training proxy for phishing.

    The consequence is measured, not theoretical: legitimate real-world
    URLs that carry a path (github.com/anthropics, docs.python.org,
    developer.mozilla.org) are flagged as phishing. Removing the
    path-derived features does NOT fix it (see
    results/phase2b/path_artifact_experiment.csv: in-domain AUC is
    preserved but the false-positive rate on real URLs is unchanged).

    This test records the defect so it cannot be forgotten. It is marked
    `xfail(strict=False)`, so it does NOT fail the suite — but if the
    defect is ever fixed the test XPASSes and pytest reports it, which
    is the signal to update the documentation.
    """

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "KNOWN DEFECT: PhiUSIIL's legitimate class has zero URLs with a "
            "path, so 'has a path' is a near-perfect training proxy for "
            "phishing and legitimate URLs with paths are misclassified. "
            "Fixing this requires multi-corpus training."
        ),
    )
    def test_legitimate_urls_with_paths_are_currently_misclassified(self) -> None:
        from app.ml.production import predict_risk_production

        # Exactly zero legitimate PhiUSIIL rows have a path.
        path = BACKEND / "datasets" / "processed" / "phiusil_clean.csv"
        if not path.exists():
            pytest.skip("processed dataset not built")

        with path.open("r", encoding="utf-8", newline="") as handle:
            legit_with_path = sum(
                1
                for record in csv.DictReader(handle)
                if record["label"] == "0" and "/" in record["normalized"].split("://")[-1]
            )
        assert legit_with_path == 0, (
            "This test assumes the corpus has zero legitimate rows with a "
            f"path; found {legit_with_path}. If the corpus changed, revisit "
            "the artifact analysis."
        )

        affected = [
            "https://github.com/anthropics",
            "https://docs.python.org/3/library/asyncio.html",
        ]
        misclassified = []
        for url in affected:
            result = predict_risk_production(normalize(url))
            if result.probability is not None and result.probability >= result.threshold:
                misclassified.append((url, round(result.probability, 4)))

        assert not misclassified, (
            "KNOWN DEFECT RESOLVED: legitimate URLs with paths are now "
            f"correctly classified. Previously misclassified: {misclassified}. "
            "If this now passes, the defect may be fixed — remove the "
            "corresponding xfail marker and update the documentation."
        )
