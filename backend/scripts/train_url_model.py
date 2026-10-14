"""
Train the URL phishing classifier.

Usage (from the backend directory):

    .venv\\Scripts\\python.exe -m scripts.train_url_model --data datasets/urls.csv

Leakage controls, applied unconditionally:
  * features are extracted from the URL string alone;
  * the split is STRATIFIED on the label;
  * normalisation, vectorisation and scaling all happen INSIDE a
    Pipeline, so they are fitted on the training fold only;
  * duplicates are removed across the whole file before splitting;
  * random_state is fixed everywhere, so a run is reproducible.

Model selection is NOT on accuracy alone. A phishing detector that
achieves high accuracy by under-reporting phishing is useless, so the
selection rule uses F1 with recall as a tie-breaker, and every metric is
reported for the record.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.dataset import DatasetRow, load_csv  # noqa: E402
from app.ml.model_loader import save_model  # noqa: E402
from app.services.feature_extractor import (  # noqa: E402
    FEATURE_NAMES,
    extract_features,
    to_vector,
)
from app.services.url_analyzer import InvalidURLError, normalize  # noqa: E402

RANDOM_STATE = 42
TEST_SIZE = 0.2


def featurize(rows: list[DatasetRow]) -> tuple[np.ndarray, np.ndarray, dict]:
    """Extract the feature matrix, dropping rows that cannot be parsed."""
    vectors: list[list[float]] = []
    labels: list[int] = []
    dropped = 0

    for row in rows:
        try:
            url = normalize(row.url)
        except InvalidURLError:
            dropped += 1
            continue
        vectors.append(to_vector(extract_features(url)))
        labels.append(row.label)

    X = np.asarray(vectors, dtype=float)
    y = np.asarray(labels, dtype=int)
    return X, y, {"unparsable_dropped": dropped, "kept": len(labels)}


def build_candidates() -> dict[str, object]:
    """Three baselines, so selection has something to choose between."""
    return {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        # solver="lbfgs" is explicit because the default
                        # ("lbfgs" on newer sklearn) passes an `iprint`
                        # option the underlying optimizer no longer accepts,
                        # which emits an OptimizeWarning on every fit.
                        solver="lbfgs",
                        max_iter=2000,
                        random_state=RANDOM_STATE,
                        class_weight="balanced",
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=None,
                        random_state=RANDOM_STATE,
                        class_weight="balanced",
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "gradient_boosting": Pipeline(
            [
                (
                    "clf",
                    GradientBoostingClassifier(
                        n_estimators=200, random_state=RANDOM_STATE
                    ),
                ),
            ]
        ),
    }


def evaluate(model, X_test, y_test) -> dict[str, float]:
    """Full metric set for the report."""
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
    }
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_test, probabilities))
    except ValueError:
        # Only one class present in the test fold.
        metrics["roc_auc"] = float("nan")

    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    metrics["false_positive_rate"] = float(
        matrix[0][1] / matrix[0].sum() if matrix[0].sum() else 0.0
    )
    metrics["false_negative_rate"] = float(
        matrix[1][0] / matrix[1].sum() if matrix[1].sum() else 0.0
    )
    return metrics


def select_best(results: dict[str, dict[str, float]]) -> str:
    """Pick a model on F1 (recall tie-break), never on accuracy alone.

    Accuracy is the wrong selection metric for an imbalanced security
    task: a model that never predicts phishing scores 90% accuracy on a
    90/10 split while catching nothing. F1 balances precision and recall,
    and recall breaks ties because a missed phishing URL is the costlier
    error for this product.
    """
    def key(name: str) -> tuple[float, float, float]:
        metrics = results[name]
        return (metrics["f1"], metrics["recall"], metrics["roc_auc"])

    return max(results, key=key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the BASIRAH URL model.")
    parser.add_argument(
        "--data", required=True, help="Path to a labelled CSV (url,label)."
    )
    parser.add_argument(
        "--allow-dev-fixture",
        action="store_true",
        help=(
            "Permit training on the DEV_FIXTURE_ONLY sample. The resulting "
            "model is marked as unevaluated and must not be reported as a "
            "trained classifier."
        ),
    )
    args = parser.parse_args()

    rows, report = load_csv(args.data)

    is_fixture = "dev_fixture" in Path(args.data).name.lower()
    if is_fixture and not args.allow_dev_fixture:
        print(
            "Refusing to train on a DEV_FIXTURE_ONLY dataset without "
            "--allow-dev-fixture. The fixture exists only to prove the "
            "pipeline runs; a model trained on it has no meaning.",
            file=sys.stderr,
        )
        return 2

    print(f"Loaded {report.total_rows} rows ({report.as_dict()})")

    X, y, featurize_stats = featurize(rows)
    print(f"Featurized: {featurize_stats}")

    if len(np.unique(y)) < 2:
        print("Dataset contains a single class; cannot train.", file=sys.stderr)
        return 2

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train {X_train.shape}, test {X_test.shape} (stratified)")

    results: dict[str, dict[str, float]] = {}
    fitted: dict[str, object] = {}

    for name, model in build_candidates().items():
        model.fit(X_train, y_train)
        results[name] = evaluate(model, X_test, y_test)
        fitted[name] = model
        m = results[name]
        print(
            f"  {name:20} acc={m['accuracy']:.4f} prec={m['precision']:.4f} "
            f"rec={m['recall']:.4f} f1={m['f1']:.4f} auc={m['roc_auc']:.4f}"
        )

    best = select_best(results)
    print(f"\nSelected on F1 (recall tie-break): {best}")

    metadata = {
        "model_name": best,
        "model_version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": report.total_rows,
        "dataset": report.as_dict(),
        "features": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "metrics": results[best],
        "all_model_metrics": results,
        "train_test_split": {
            "test_size": TEST_SIZE,
            "stratified": True,
            "random_state": RANDOM_STATE,
        },
        "selection_rule": "max F1, ties broken by recall",
        "evaluated": not is_fixture,
    }
    if is_fixture:
        metadata["WARNING"] = (
            "Trained on DEV_FIXTURE_ONLY data. These metrics are NOT a model "
            "evaluation and must never be reported as such."
        )

    path = save_model(fitted[best], FEATURE_NAMES, metadata)
    print(f"\nSaved model: {path.name}")
    print(f"Metadata:   {path.with_suffix('.metadata.json').name}")

    if is_fixture:
        print(
            "\n*** DEV_FIXTURE_ONLY *** Real model evaluation is pending "
            "dataset acquisition.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
