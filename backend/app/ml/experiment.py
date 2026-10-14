"""
Model definitions, evaluation metrics, calibration and threshold tuning.

Kept separate from the experiment runner so each concern is testable in
isolation and the runner stays readable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

RANDOM_STATE = 42


# ====================================================================
# METRICS
# ====================================================================


@dataclass
class MetricSet:
    """Full metric suite for one model/split/threshold combination."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    fpr: float
    fnr: float
    specificity: float
    balanced_accuracy: float
    brier: float
    average_precision: float
    threshold: float = 0.5
    inference_ms: float = 0.0
    model_size_mb: float = 0.0
    extras: dict[str, object] = field(default_factory=dict)

    def as_row(self) -> dict[str, object]:
        return {
            "accuracy": round(self.accuracy, 6),
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "f1": round(self.f1, 6),
            "roc_auc": round(self.roc_auc, 6),
            "fpr": round(self.fpr, 6),
            "fnr": round(self.fnr, 6),
            "specificity": round(self.specificity, 6),
            "balanced_accuracy": round(self.balanced_accuracy, 6),
            "brier": round(self.brier, 6),
            "average_precision": round(self.average_precision, 6),
            "threshold": round(self.threshold, 6),
            "inference_ms": round(self.inference_ms, 4),
            "model_size_mb": round(self.model_size_mb, 4),
        }


def compute_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float = 0.5,
    inference_ms: float = 0.0,
    model_size_mb: float = 0.0,
) -> MetricSet:
    """Every metric Phase 2B requires, from probabilities + a threshold.

    FPR and FNR are derived from the confusion matrix explicitly rather
    than taken from sklearn's `zero_division` defaults, so a degenerate
    fold cannot silently report a reassuring zero.
    """
    predictions = (probabilities >= threshold).astype(int)

    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    tn, fp = int(matrix[0][0]), int(matrix[0][1])
    fn, tp = int(matrix[1][0]), int(matrix[1][1])

    # A fold containing no positives cannot produce a rate; NaN is honest,
    # where a defaulted 0.0 would read as "no false positives".
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    fnr = fn / (fn + tp) if (fn + tp) else float("nan")

    specificity = tn / (tn + fp) if (tn + fp) else float("nan")

    try:
        auc = float(roc_auc_score(y_true, probabilities))
    except ValueError:
        auc = float("nan")
    try:
        ap = float(average_precision_score(y_true, probabilities))
    except ValueError:
        ap = float("nan")

    return MetricSet(
        accuracy=float(accuracy_score(y_true, predictions)),
        precision=float(precision_score(y_true, predictions, zero_division=0)),
        recall=float(recall_score(y_true, predictions, zero_division=0)),
        f1=float(f1_score(y_true, predictions, zero_division=0)),
        roc_auc=auc,
        fpr=fpr,
        fnr=fnr,
        specificity=specificity,
        balanced_accuracy=float(
            (recall_score(y_true, predictions, zero_division=0) + specificity) / 2
        )
        if specificity == specificity
        else float("nan"),
        brier=float(brier_score_loss(y_true, probabilities)),
        average_precision=ap,
        threshold=threshold,
        inference_ms=inference_ms,
        model_size_mb=model_size_mb,
        extras={"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    )


# ====================================================================
# MODELS
# ====================================================================


def build_models() -> dict[str, Callable[[], object]]:
    """The candidate models, each wrapped so scaling stays train-only.

    `class_weight="balanced"` matters here: PhiUSIIL is ~57/43, mild
    imbalance, but a future corpus may not be, and the cost of missing a
    phishing URL exceeds the cost of a false alarm.
    """
    from xgboost import XGBClassifier

    return {
        "logistic_regression": lambda: LogisticRegression(
            max_iter=3000,
            random_state=RANDOM_STATE,
            class_weight="balanced",
            solver="lbfgs",
        ),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=1,
            random_state=RANDOM_STATE,
            class_weight="balanced_subsample",
            n_jobs=-1,
        ),
        "xgboost": lambda: XGBClassifier(
            n_estimators=400,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=1,
            reg_lambda=1.0,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            tree_method="hist",
            eval_metric="logloss",
        ),
        "hist_gradient_boosting": lambda: GradientBoostingClassifier(
            n_estimators=300, random_state=RANDOM_STATE
        ),
    }


def model_file_size_mb(model: object) -> float:
    """Serialised size, in MB."""
    import io
    import joblib

    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    return buffer.getbuffer().nbytes / (1024 * 1024)


def timed_probabilities(model: object, X: np.ndarray) -> tuple[np.ndarray, float]:
    """Predict and measure single-threaded inference latency in ms."""
    # Warm up: the first call includes lazy initialisation and would
    # overstate steady-state latency.
    model.predict_proba(X[: min(256, len(X))])  # type: ignore[attr-defined]

    start = time.perf_counter()
    probabilities = model.predict_proba(X)[:, 1]  # type: ignore[attr-defined]
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return probabilities, elapsed_ms


def positive_class_index(model: object) -> int:
    """Column index of the positive class in predict_proba.

    Read from `classes_` rather than assumed to be 1, so a model whose
    class ordering differs cannot silently return inverted scores.
    """
    classes = list(getattr(model, "classes_", [0, 1]))
    return classes.index(1)


# ====================================================================
# CALIBRATION
# ====================================================================


def fit_platt_scaler(
    probabilities: np.ndarray, y: np.ndarray
) -> tuple[float, float]:
    """Platt scaling on the logit of the raw probability.

    Fitted on VALIDATION data only. Returns (a, b) such that
    calibrated = sigmoid(a * logit(p) + b).
    """
    from sklearn.linear_model import LogisticRegression

    eps = 1e-6
    clipped = np.clip(probabilities, eps, 1 - eps)
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)

    calibrator = LogisticRegression(random_state=RANDOM_STATE)
    calibrator.fit(logits, y)
    return float(calibrator.coef_[0][0]), float(calibrator.intercept_[0])


def apply_platt(probabilities: np.ndarray, a: float, b: float) -> np.ndarray:
    eps = 1e-6
    clipped = np.clip(probabilities, eps, 1 - eps)
    logits = np.log(clipped / (1 - clipped))
    return 1.0 / (1.0 + np.exp(-(a * logits + b)))


def fit_isotonic(probabilities: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    """Isotonic regression, fitted on validation data only."""
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(probabilities, y)
    return calibrator


def calibration_report(
    y_true: np.ndarray,
    raw: np.ndarray,
    platt: np.ndarray,
    isotonic: np.ndarray,
) -> dict[str, float]:
    """Brier score for each probability source, plus the best method."""
    scores = {
        "brier_raw": float(brier_score_loss(y_true, raw)),
        "brier_platt": float(brier_score_loss(y_true, platt)),
        "brier_isotonic": float(brier_score_loss(y_true, isotonic)),
    }
    # Lower Brier is better.
    best = min(scores, key=scores.get)
    scores["best"] = best
    scores["brier_improvement"] = scores["brier_raw"] - scores[best]
    return scores


# ====================================================================
# THRESHOLD TUNING
# ====================================================================


def select_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    min_recall: float = 0.90,
) -> tuple[float, dict[str, object]]:
    """Choose an operating threshold from VALIDATION data.

    Strategy: take the HIGHEST threshold that still satisfies the recall
    floor. This maximises specificity (and therefore lowers the false
    positive rate) subject to not missing more than `1 - min_recall` of
    phishing URLs.

    Rationale: for this product a missed phishing URL is the costlier
    error, so recall is a constraint rather than an objective, and
    precision is what we maximise within it.

    Tuned on validation only — never on the test set.
    """
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)

    # Start BELOW any achievable threshold. Initialising to 0.5 made
    # every candidate below 0.5 permanently ineligible via
    # `candidate >= best_threshold`, so a model whose optimum sits under
    # 0.5 silently fell through to the best-F1 fallback and reported
    # that the recall floor was "not reachable" when it was. -1.0 is
    # below every real probability.
    best_threshold = -1.0
    best_metrics: dict[str, object] = {}

    # precision/recall have length len(thresholds)+1; align them.
    for index in range(len(thresholds)):
        current_recall = recall[index]
        current_precision = precision[index]
        if current_recall >= min_recall:
            # Highest threshold satisfying the floor wins, because a
            # higher threshold means fewer false alarms.
            candidate = float(thresholds[index])
            if candidate >= best_threshold:
                predictions = (probabilities >= candidate).astype(int)
                best_threshold = candidate
                best_metrics = {
                    "threshold": round(candidate, 4),
                    "recall": round(float(current_recall), 4),
                    "precision": round(float(current_precision), 4),
                    "f1": round(
                        float(
                            f1_score(
                                y_true,
                                predictions,
                                zero_division=0,
                            )
                        ),
                        4,
                    ),
                    "selected_by": "highest threshold meeting the recall floor",
                }

    if not best_metrics:
        # The floor is unreachable; fall back to the best-F1 threshold and
        # say so, rather than silently pretending the constraint was met.
        f1_values = [
            f1_score(y_true, (probabilities >= t).astype(int), zero_division=0)
            for t in thresholds
        ]
        best_index = int(np.argmax(f1_values))
        best_threshold = float(thresholds[best_index])
        best_metrics = {
            "threshold": round(best_threshold, 4),
            "recall": round(float(recall[best_index]), 4),
            "precision": round(float(precision[best_index]), 4),
            "f1": round(float(f1_values[best_index]), 4),
            "selected_by": "best F1 — the recall floor was not reachable",
            "recall_floor_met": False,
        }
    else:
        best_metrics["recall_floor_met"] = True

    best_metrics["min_recall_target"] = min_recall
    return best_threshold, best_metrics
