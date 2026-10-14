"""
Tests for dataset loading, label normalisation and the training
pipeline's guard rails.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ml.dataset import DatasetError, load_csv, normalize_label

FIXTURE = Path(__file__).resolve().parents[1] / "datasets" / "dev_fixture_urls.csv"


class TestLabelNormalisation:
    @pytest.mark.parametrize(
        "raw", ["1", "true", "YES", "phishing", "Phish", "malicious", "bad", "fraud", "1.0"]
    )
    def test_phishing_vocabulary(self, raw: str) -> None:
        assert normalize_label(raw) == 1

    @pytest.mark.parametrize(
        "raw",
        ["0", "false", "no", "legit", "legitimate", "BENIGN", "good", "safe", "normal", "0.0"],
    )
    def test_benign_vocabulary(self, raw: str) -> None:
        assert normalize_label(raw) == 0

    def test_whitespace_tolerated(self) -> None:
        assert normalize_label("  phishing  ") == 1

    @pytest.mark.parametrize("raw", ["maybe", "", "2", "-1", "unknown"])
    def test_unknown_label_raises(self, raw: str) -> None:
        """Never coerce an unrecognised label — it would poison training."""
        with pytest.raises(DatasetError):
            normalize_label(raw)


class TestColumnDetection:
    def test_finds_url_and_label(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text("url,label\nhttps://a.com,0\n", encoding="utf-8")
        rows, report = load_csv(path)
        assert len(rows) == 1
        assert "url" in report.columns_found

    def test_tolerates_alternative_names(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text("uri,class\nhttps://a.com,benign\n", encoding="utf-8")
        rows, _ = load_csv(path)
        assert rows[0].label == 0

    def test_missing_url_column_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text("link_name,label\na,0\n", encoding="utf-8")
        with pytest.raises(DatasetError, match="No URL column"):
            load_csv(path)

    def test_missing_label_column_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text("url,result\na,0\n", encoding="utf-8")
        with pytest.raises(DatasetError, match="No label column"):
            load_csv(path)

    def test_missing_file_raises(self) -> None:
        with pytest.raises(DatasetError, match="not found"):
            load_csv("does_not_exist.csv")

    def test_header_only_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text("url,label\n", encoding="utf-8")
        with pytest.raises(DatasetError, match="No usable rows"):
            load_csv(path)


class TestRowCleaning:
    def test_skips_blank_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text(
            "url,label\nhttps://a.com,0\n,0\nhttps://b.com,\nhttps://c.com,1\n",
            encoding="utf-8",
        )
        rows, report = load_csv(path)
        assert len(rows) == 2
        assert report.skipped_invalid == 2

    def test_deduplicates(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text(
            "url,label\nhttps://a.com,0\nhttps://A.com,0\nhttps://b.com,1\n",
            encoding="utf-8",
        )
        rows, report = load_csv(path)
        assert len(rows) == 2
        assert report.skipped_duplicate == 1

    def test_handles_utf8_bom(self, tmp_path: Path) -> None:
        """Excel-exported CSVs carry a BOM that breaks naive parsing."""
        path = tmp_path / "d.csv"
        path.write_bytes("url,label\nhttps://a.com,0\n".encode("utf-8-sig"))
        rows, _ = load_csv(path)
        assert len(rows) == 1

    def test_reports_class_balance(self, tmp_path: Path) -> None:
        path = tmp_path / "d.csv"
        path.write_text(
            "url,label\nhttps://a.com,0\nhttps://b.com,0\nhttps://c.com,1\n",
            encoding="utf-8",
        )
        _, report = load_csv(path)
        assert report.benign_rows == 2
        assert report.phishing_rows == 1
        assert report.is_balanced is False
        assert report.total_rows == 3


class TestDevFixture:
    """The fixture must load, and must be unmistakable about what it is."""

    def test_fixture_loads(self) -> None:
        rows, report = load_csv(FIXTURE)
        assert len(rows) == 20
        assert report.total_rows == 20

    def test_fixture_is_balanced(self) -> None:
        _, report = load_csv(FIXTURE)
        assert report.is_balanced

    def test_fixture_name_marks_it_as_dev_only(self) -> None:
        """The training guard keys off this name, so it must stay stable."""
        assert "dev_fixture" in FIXTURE.name.lower()


class TestTrainingGuards:
    def test_no_shipped_model_in_the_repository(self) -> None:
        """The repo must ship without a fixture-trained model.

        Shipping one would make the API report a model that was trained on
        20 hand-written rows, which is exactly the dishonesty this project
        is meant to avoid.
        """
        models_dir = Path(__file__).resolve().parents[1] / "models"
        bundle = models_dir / "url_risk_model.joblib"
        assert not bundle.exists(), (
            "A trained model is committed. It must be produced locally from a "
            "real dataset, not shipped."
        )

    def test_model_status_reports_unavailable(self) -> None:
        from app.ml.model_loader import model_status

        status = model_status()
        if not status.available:
            assert "No trained model" in status.reason
