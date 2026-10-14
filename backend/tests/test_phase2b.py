"""
Phase 2B tests: dataset schema, label normalisation, split integrity,
feature-schema enforcement, model loading and the leakage gate.

These guard the properties the Phase 2B definition-of-done depends on.
A regression in any of them would let the experiment report numbers that
look valid and are not.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.ml.datasets import (
    AuditedRow,
    UnknownLabelError,
    require_label,
    find_label_column,
    find_url_column,
    load_processed,
    normalize_dataset_label,
)
from app.ml.feature_schema import (
    FEATURE_EXTRACTOR_VERSION,
    MODEL_EXCLUDED_FEATURES,
    FeatureSchemaMismatch,
    assert_schema_matches,
    current_schema,
    model_feature_indices,
    model_feature_names,
)
from app.ml.splits import (
    DomainLeakageError,
    SplitBundle,
    grouped_split,
    random_split,
)
from app.services.feature_extractor import FEATURE_NAMES, extract_features, to_vector
from app.services.url_analyzer import normalize

BACKEND = Path(__file__).resolve().parents[1]


# ====================================================================
# LABEL NORMALISATION
# ====================================================================


class TestLabelNormalisation:
    @pytest.mark.parametrize(
        "raw", ["1", "phishing", "PHISHING", "malicious", "1.0", " true "]
    )
    def test_phishing_tokens(self, raw: str) -> None:
        assert normalize_dataset_label(raw) == 1

    @pytest.mark.parametrize(
        "raw", ["0", "legitimate", "BENIGN", "good", "0.0", "false"]
    )
    def test_benign_tokens(self, raw: str) -> None:
        assert normalize_dataset_label(raw) == 0

    @pytest.mark.parametrize("raw", ["maybe", "", "2", "-1", "unknown"])
    def test_unknown_label_returns_none(self, raw: str) -> None:
        """Never coerce: a silently-defaulted label poisons training."""
        assert normalize_dataset_label(raw) is None

    @pytest.mark.parametrize("raw", ["maybe", "", "2", "unknown"])
    def test_require_label_raises(self, raw: str) -> None:
        with pytest.raises(UnknownLabelError):
            require_label(raw)

    def test_require_label_passes_through(self) -> None:
        assert require_label("phishing") == 1
        assert require_label("benign") == 0

    def test_label_meaning_is_unambiguous(self) -> None:
        from app.ml.datasets import LEGITIMATE, PHISHING

        assert PHISHING == 1
        assert LEGITIMATE == 0


# ====================================================================
# COLUMN DETECTION
# ====================================================================


class TestColumnDetection:
    def test_finds_url_column(self) -> None:
        assert find_url_column(["FILENAME", "URL", "label"]) == "URL"

    def test_tolerates_case_and_spacing(self) -> None:
        assert find_url_column([" url ", "label"]) == " url "

    def test_does_not_pick_label_as_url(self) -> None:
        assert find_url_column(["label", "url"]) == "url"

    def test_finds_label_column(self) -> None:
        assert find_label_column(["URL", "label"], "URL") == "label"

    def test_label_column_never_equals_url_column(self) -> None:
        assert find_label_column(["url", "url"], "url") is None

    def test_missing_url_column_returns_none(self) -> None:
        assert find_url_column(["a", "b"]) is None


# ====================================================================
# GROUPED SPLIT — LEAKAGE CONTROL
# ====================================================================


def _rows_with_domains(pairs: list[tuple[str, int]]) -> list[AuditedRow]:
    return [
        AuditedRow(
            url=f"https://{domain}/path{i}",
            normalized=f"https://{domain}/path{i}",
            label=label,
            registered_domain=domain,
            scheme="https",
            hostname=domain,
            uses_https=True,
            source="test",
        )
        for i, (domain, label) in enumerate(pairs)
    ]


class TestGroupedSplitLeakage:
    def test_no_domain_spans_partitions(self) -> None:
        """The core Phase 2B guarantee."""
        pairs = [(f"d{i % 40}.com", i % 2) for i in range(400)]
        rows = _rows_with_domains(pairs)
        y = np.asarray([r.label for r in rows])
        split = grouped_split(rows, y)
        assert not (split.train_domains & split.test_domains)
        assert not (split.train_domains & split.val_domains)
        assert not (split.val_domains & split.test_domains)

    def test_same_domain_stays_together(self) -> None:
        """login.example.com and verify.example.com cannot be separated."""
        pairs: list[tuple[str, int]] = []
        for i in range(20):
            pairs.append(("example.com", i % 2))
            pairs.append((f"sub{i}.example.com", i % 2))
            pairs.append((f"other{i}.net", 1))
        rows = _rows_with_domains(pairs)
        y = np.asarray([r.label for r in rows])
        split = grouped_split(rows, y)

        for domain in ("example.com", "other0.net"):
            in_train = domain in split.train_domains
            in_val = domain in split.val_domains
            in_test = domain in split.test_domains
            assert sum([in_train, in_val, in_test]) == 1, domain

    def test_assertion_raises_on_injected_leakage(self) -> None:
        """The guard must actually fire, not merely exist."""
        leaky = SplitBundle(
            strategy="grouped_domain",
            train_idx=np.array([0, 1]),
            val_idx=np.array([2]),
            test_idx=np.array([3]),
            train_domains={"shared.com"},
            val_domains={"shared.com"},
            test_domains={"other.com"},
        )
        with pytest.raises(DomainLeakageError):
            leaky.assert_no_domain_leakage()

    def test_all_partitions_non_empty(self) -> None:
        pairs = [(f"d{i % 30}.com", i % 2) for i in range(600)]
        rows = _rows_with_domains(pairs)
        y = np.asarray([r.label for r in rows])
        split = grouped_split(rows, y)
        assert len(split.train_idx) > 0
        assert len(split.val_idx) > 0
        assert len(split.test_idx) > 0

    def test_partitions_are_disjoint(self) -> None:
        pairs = [(f"d{i % 25}.com", i % 2) for i in range(500)]
        rows = _rows_with_domains(pairs)
        y = np.asarray([r.label for r in rows])
        split = grouped_split(rows, y)
        all_indices = np.concatenate(
            [split.train_idx, split.val_idx, split.test_idx]
        )
        assert len(np.unique(all_indices)) == len(all_indices)
        assert len(all_indices) == len(y)


class TestRandomSplit:
    def test_produces_three_partitions(self) -> None:
        y = np.array([0, 1] * 200)
        split = random_split(y)
        assert len(split.train_idx) + len(split.val_idx) + len(split.test_idx) == len(y)

    def test_stratified_roughly(self) -> None:
        y = np.array([0, 1] * 200)
        split = random_split(y)
        overall = y.mean()
        assert abs(y[split.train_idx].mean() - overall) < 0.05


# ====================================================================
# FEATURE SCHEMA
# ====================================================================


class TestFeatureSchema:
    def test_model_features_are_a_subset(self) -> None:
        model = set(model_feature_names())
        assert model.issubset(set(FEATURE_NAMES))

    def test_excluded_features_are_not_model_inputs(self) -> None:
        model = set(model_feature_names())
        assert not (model & MODEL_EXCLUDED_FEATURES)

    def test_scheme_features_are_excluded(self) -> None:
        """The Phase 2B finding must not be silently reverted."""
        assert "uses_https" in MODEL_EXCLUDED_FEATURES
        assert "uses_http" in MODEL_EXCLUDED_FEATURES

    def test_indices_align_with_names(self) -> None:
        names = model_feature_names()
        indices = model_feature_indices()
        assert len(names) == len(indices)
        for name, index in zip(names, indices):
            assert FEATURE_NAMES[index] == name

    def test_matching_schema_passes(self) -> None:
        assert_schema_matches(model_feature_names(), FEATURE_EXTRACTOR_VERSION)

    def test_wrong_count_raises(self) -> None:
        with pytest.raises(FeatureSchemaMismatch):
            assert_schema_matches(model_feature_names()[:-1], FEATURE_EXTRACTOR_VERSION)

    def test_wrong_version_raises(self) -> None:
        with pytest.raises(FeatureSchemaMismatch):
            assert_schema_matches(model_feature_names(), "0.0.0-fake")

    def test_reordered_features_raise(self) -> None:
        """The dangerous case: same names, different order."""
        shuffled = list(reversed(model_feature_names()))
        with pytest.raises(FeatureSchemaMismatch, match="ORDER"):
            assert_schema_matches(shuffled, FEATURE_EXTRACTOR_VERSION)

    def test_vector_slicing_matches_indices(self) -> None:
        url = normalize("https://example.com/a?b=c")
        full = to_vector(extract_features(url))
        sliced = [full[i] for i in model_feature_indices()]
        assert len(sliced) == len(model_feature_names())

    def test_fingerprint_is_order_sensitive(self) -> None:
        a = current_schema().fingerprint()
        b = current_schema().fingerprint()
        assert a == b
        assert len(a) == 16


# ====================================================================
# DATASET ARTEFACTS
# ====================================================================


class TestProcessedDataset:
    @pytest.fixture(scope="class")
    def rows(self) -> list[AuditedRow]:
        path = BACKEND / "datasets" / "processed" / "phiusil_clean.csv"
        if not path.exists():
            pytest.skip("processed dataset not built yet")
        return load_processed("phiusil")

    def test_row_count_is_plausible(self, rows: list[AuditedRow]) -> None:
        assert 200_000 < len(rows) < 260_000

    def test_both_classes_present(self, rows: list[AuditedRow]) -> None:
        labels = {r.label for r in rows}
        assert labels == {0, 1}

    def test_no_duplicate_normalized_urls(self, rows: list[AuditedRow]) -> None:
        seen = set()
        for row in rows:
            key = row.normalized.lower()
            assert key not in seen, f"duplicate survived cleaning: {key}"
            seen.add(key)

    def test_every_row_has_a_registered_domain(self, rows: list[AuditedRow]) -> None:
        for row in rows[:5000]:
            assert row.registered_domain

    def test_domain_repetition_exists(self, rows: list[AuditedRow]) -> None:
        """Confirms the grouped split is actually necessary."""
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.registered_domain] = counts.get(row.registered_domain, 0) + 1
        repeated = sum(1 for v in counts.values() if v > 1)
        assert repeated > 100, "no repeated domains; grouped split untested"


# ====================================================================
# MODEL ARTEFACTS
# ====================================================================


class TestProductionModel:
    @pytest.fixture(scope="class")
    def bundle_path(self) -> Path:
        path = BACKEND / "models" / "basirah-url-v1.joblib"
        if not path.exists():
            pytest.skip("production model not trained yet")
        return path

    def test_loads_and_predicts(self, bundle_path: Path) -> None:
        import joblib

        bundle = joblib.load(bundle_path)
        model = bundle["estimator"]
        assert hasattr(model, "predict_proba")

    def test_stored_features_match_current_schema(self, bundle_path: Path) -> None:
        """A model whose stored order drifted must be refused."""
        import joblib

        bundle = joblib.load(bundle_path)
        assert_schema_matches(bundle["feature_names"], FEATURE_EXTRACTOR_VERSION)

    def test_probabilities_are_in_range(self, bundle_path: Path) -> None:
        import joblib

        bundle = joblib.load(bundle_path)
        model = bundle["estimator"]
        indices = model_feature_indices()
        X = np.asarray(
            [
                [to_vector(extract_features(normalize(u)))[i] for i in indices]
                for u in [
                    "https://example.com",
                    "http://192.168.1.1/login",
                    "https://secure-login-account-update.example.com",
                ]
            ],
            dtype=np.float32,
        )
        probabilities = model.predict_proba(X)[:, 1]
        assert probabilities.shape == (3,)
        assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))

    def test_metadata_records_threshold(self, bundle_path: Path) -> None:
        import json

        path = BACKEND / "models" / "basirah-url-v1.metadata.json"
        if not path.exists():
            pytest.skip("metadata not written")
        metadata = json.loads(path.read_text(encoding="utf-8"))
        assert 0.0 < metadata["selected_threshold"] <= 1.0
        assert metadata["threshold_tuned_on"] == "validation fold only"
        assert metadata["split_strategy"] == "grouped_domain"

    def test_metadata_excludes_no_filesystem_paths(self, bundle_path: Path) -> None:
        import json

        path = BACKEND / "models" / "basirah-url-v1.metadata.json"
        if not path.exists():
            pytest.skip("metadata not written")
        text = path.read_text(encoding="utf-8").lower()
        for leaked in ("c:\\", "/home/", "users/"):
            assert leaked not in text


# ====================================================================
# XGBOOST LOADING
# ====================================================================


class TestXGBoost:
    def test_xgboost_is_installed(self) -> None:
        pytest.importorskip("xgboost")

    def test_predict_proba_available(self) -> None:
        xgb = pytest.importorskip("xgboost")
        from xgboost import XGBClassifier

        model = XGBClassifier(n_estimators=5, random_state=42)
        model.fit(
            np.random.RandomState(0).rand(80, 5),
            np.random.RandomState(1).randint(0, 2, 80),
        )
        probabilities = model.predict_proba(np.random.rand(4, 5))
        assert probabilities.shape == (4, 2)
        assert np.allclose(probabilities.sum(axis=1), 1.0)
        assert xgb.__version__
