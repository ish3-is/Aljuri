"""
Phase 2C stages: the pieces the orchestrator composes.

Kept separate so each concern is testable and the runner reads as a
stage list rather than a wall of code.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from app.ml.datasets import AuditedRow
from app.ml.datasets import LEGITIMATE, PHISHING
from app.ml.feature_schema import model_feature_indices, model_feature_names
from app.ml.semantic_cases import ALL_CASES, SemanticCase
from app.services.feature_extractor import FEATURE_NAMES, extract_features, to_vector
from app.services.heuristic_engine import evaluate, heuristic_risk
from app.services.url_analyzer import InvalidURLError, normalize

BACKEND = Path(__file__).resolve().parents[2]


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


# ====================================================================
# FEATURIZATION
# ====================================================================


def featurize(urls: Sequence[str], label: str = "", report_every: int = 50_000) -> np.ndarray:
    """Run every URL through BASIRAH's production extractor.

    The full 41-feature output is returned, not the model's 39-column
    slice, because several analyses (robustness slices, stability
    classification) legitimately need the excluded columns too.
    """
    vectors: list[list[float]] = []
    dropped = 0
    started = time.perf_counter()

    for index, url in enumerate(urls):
        try:
            parsed = normalize(url)
        except InvalidURLError:
            dropped += 1
            continue
        vectors.append(to_vector(extract_features(parsed)))
        if label and report_every and index and index % report_every == 0:
            rate = index / max(time.perf_counter() - started, 1e-9)
            log(f"    {label}: {index:,}/{len(urls):,} ({rate:,.0f}/s)")

    if dropped:
        log(f"    {label}: dropped {dropped:,} unparsable URLs")
    return np.asarray(vectors, dtype=np.float32)


# ====================================================================
# CORPUS-SOURCE CLASSIFIER (source bias diagnostic)
# ====================================================================


def corpus_classifier_metrics(
    matrices: dict[str, np.ndarray],
    seed: int = 42,
    columns: Sequence[int] | None = None,
    label_suffix: str = "",
) -> dict[str, Any]:
    """Can a model tell which corpus a URL came from?

    This is the source-bias diagnostic. If a classifier separates the
    corpora almost perfectly using the same features the phishing model
    uses, then the corpora encode different collection methodologies,
    and any phishing score is partly a corpus fingerprint.

    The diagnostic model is NEVER used in production — it exists only to
    quantify how separable the sources are.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score

    names = sorted(matrices)
    if len(names) < 2:
        return {"available": False, "reason": "fewer than two corpora"}

    X_parts, y_parts = [], []
    for index, corpus in enumerate(names):
        X = matrices[corpus]
        if columns is not None:
            X = X[:, columns]
        X_parts.append(X)
        y_parts.append(np.full(len(X), index))
    X = np.vstack(X_parts)
    y = np.concatenate(y_parts)

    from sklearn.model_selection import train_test_split

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )
    probe = RandomForestClassifier(
        n_estimators=120, random_state=seed, n_jobs=-1, class_weight="balanced"
    )
    probe.fit(X_tr, y_tr)
    predictions = probe.predict(X_te)
    probabilities = probe.predict_proba(X_te)[:, 1]

    accuracy = float(accuracy_score(y_te, predictions))
    try:
        auc = float(roc_auc_score(y_te, probabilities))
    except ValueError:
        auc = float("nan")

    return {
        "available": True,
        "label_suffix": label_suffix,
        "n_rows": int(len(y)),
        "corpora": names,
        "corpus_classifier_accuracy": round(accuracy, 6),
        "corpus_classifier_auc": round(auc, 6),
        "chance_accuracy": round(1.0 / len(names), 6),
        "n_features": int(X.shape[1]),
        "interpretation": (
            "near-perfect separation means the corpora encode different "
            "collection methodologies; a phishing score is partly a corpus "
            "fingerprint"
            if accuracy > 0.90
            else "corpora are not trivially separable on these features"
        ),
    }


# ====================================================================
# SEMANTIC REGRESSION
# ====================================================================


def evaluate_semantic_cases(
    estimator: object,
    threshold: float,
    columns: Sequence[int],
    cases: Sequence[SemanticCase] = ALL_CASES,
) -> dict[str, Any]:
    """Score the semantic regression set.

    Returns per-case outcomes plus aggregate counts. A false positive on
    a well-known legitimate URL is treated as a first-class failure,
    because that is the failure a corpus metric cannot see.
    """
    if not cases:
        return {"available": False}

    rows: list[dict[str, Any]] = []
    for case in cases:
        try:
            parsed = normalize(case.url)
        except InvalidURLError:
            rows.append(
                {
                    "url": case.url, "category": case.category,
                    "expected": case.expected_label, "probability": None,
                    "predicted": None, "correct": False, "note": "unparsable",
                }
            )
            continue
        full = to_vector(extract_features(parsed))
        vector = [full[i] for i in columns]
        probabilities = estimator.predict_proba([vector])  # type: ignore[attr-defined]
        classes = list(getattr(estimator, "classes_", [0, 1]))
        column = classes.index(1) if 1 in classes else len(classes) - 1
        probability = float(probabilities[0][column])
        predicted = 1 if probability >= threshold else 0
        rows.append(
            {
                "url": case.url,
                "category": case.category,
                "rationale": case.rationale,
                "expected": case.expected_label,
                "expected_name": "phishing" if case.expected_label == PHISHING else "legitimate",
                "probability": round(probability, 6),
                "predicted": predicted,
                "correct": predicted == case.expected_label,
            }
        )

    legitimate = [r for r in rows if r["expected"] == LEGITIMATE]
    phishing = [r for r in rows if r["expected"] == PHISHING]
    fp = [r for r in legitimate if r["predicted"] == PHISHING]
    fn = [r for r in phishing if r["predicted"] == LEGITIMATE]

    return {
        "available": True,
        "threshold": round(threshold, 6),
        "n_cases": len(rows),
        "n_legitimate": len(legitimate),
        "n_phishing": len(phishing),
        "legitimate_false_positives": len(fp),
        "phishing_false_negatives": len(fn),
        "legitimate_fp_rate": round(len(fp) / max(len(legitimate), 1), 6),
        "phishing_detection_rate": round(
            (len(phishing) - len(fn)) / max(len(phishing), 1), 6
        ),
        "accuracy": round(
            sum(1 for r in rows if r["correct"]) / max(len(rows), 1), 6
        ),
        "cases": rows,
    }


def real_world_regression(
    estimator: object,
    threshold: float,
    columns: Sequence[int],
    urls: Sequence[str],
) -> dict[str, Any]:
    """False-positive rate on real, well-known legitimate URLs."""
    flags: list[dict[str, Any]] = []
    for url in urls:
        try:
            parsed = normalize(url)
        except InvalidURLError:
            continue
        full = to_vector(extract_features(parsed))
        vector = [full[i] for i in columns]
        probabilities = estimator.predict_proba([vector])  # type: ignore[attr-defined]
        classes = list(getattr(estimator, "classes_", [0, 1]))
        column = classes.index(1) if 1 in classes else len(classes) - 1
        probability = float(probabilities[0][column])
        flags.append(
            {
                "url": url,
                "probability": round(probability, 6),
                "flagged": probability >= threshold,
            }
        )
    flagged = [f for f in flags if f["flagged"]]
    return {
        "n": len(flags),
        "flagged": len(flagged),
        "false_positive_rate": round(len(flagged) / max(len(flags), 1), 6),
        "cases": sorted(flags, key=lambda f: -f["probability"]),
    }


# ====================================================================
# HEURISTICS
# ====================================================================


def heuristic_risk_column(rows: Sequence[AuditedRow], indices: np.ndarray | None = None) -> np.ndarray:
    """Heuristic risk (0-100) from the production engine."""
    selected = [rows[int(i)] for i in indices] if indices is not None else list(rows)
    out = np.zeros(len(selected), dtype=np.float32)
    for position, row in enumerate(selected):
        try:
            parsed = normalize(row.url)
        except InvalidURLError:
            continue
        score, _ = heuristic_risk(evaluate(parsed))
        out[position] = score
    return out


def heuristic_analysis(rows: Sequence[AuditedRow], labels: np.ndarray, sample: int = 40000, seed: int = 42) -> list[dict[str, Any]]:
    """Per-rule precision, coverage and redundancy with the ML model.

    Phase 2B established the rules are precise but low-coverage. Phase 2C
    additionally measures REDUNDANCY: if a rule fires almost entirely on
    rows the model already scores highly, it adds explanation but no
    detection power. That is the justification for keeping the heuristic
    engine as an evidence layer rather than a scoring component.
    """
    rng = np.random.default_rng(seed)
    indices = (
        np.arange(len(rows)) if len(rows) <= sample
        else rng.choice(len(rows), size=sample, replace=False)
    )

    stats: dict[str, dict[str, int]] = {}
    for index in indices:
        try:
            parsed = normalize(rows[int(index)].url)
        except InvalidURLError:
            continue
        label = int(labels[int(index)])
        for finding in evaluate(parsed):
            entry = stats.setdefault(
                finding.id,
                {"triggered": 0, "tp": 0, "fp": 0, "phish": 0, "legit": 0},
            )
            entry["phish" if label == PHISHING else "legit"] += 1
            if finding.triggered:
                entry["triggered"] += 1
                if label == PHISHING:
                    entry["tp"] += 1
                else:
                    entry["fp"] += 1

    evaluated = sum(e["phish"] + e["legit"] for e in stats.values()) / max(len(stats), 1)
    rows_out: list[dict[str, Any]] = []
    for rule_id, entry in stats.items():
        trig = entry["triggered"]
        precision = entry["tp"] / trig if trig else float("nan")
        coverage = entry["tp"] / max(entry["phish"], 1)
        legit_rate = entry["fp"] / max(entry["legit"], 1)
        if trig == 0:
            role = "never_fires"
        elif precision != precision:
            role = "no_data"
        elif precision >= 0.90:
            role = "strong"
        elif precision >= 0.70:
            role = "supporting"
        else:
            role = "noisy"
        rows_out.append(
            {
                "rule_id": rule_id,
                "times_triggered": int(trig),
                "trigger_frequency": round(trig / evaluated, 6) if evaluated else 0.0,
                "precision_when_triggered": round(precision, 6) if precision == precision else None,
                "phishing_coverage": round(coverage, 6),
                "legitimate_trigger_rate": round(legit_rate, 6),
                "role": role,
            }
        )
    return sorted(rows_out, key=lambda r: -(r["precision_when_triggered"] or 0))


def heuristic_any_triggered(rows: Sequence[AuditedRow], indices: np.ndarray) -> np.ndarray:
    """1 where ANY heuristic rule fired. Used for redundancy analysis."""
    out = np.zeros(len(indices), dtype=np.float32)
    for position, index in enumerate(indices):
        try:
            parsed = normalize(rows[int(index)].url)
        except InvalidURLError:
            continue
        findings = evaluate(parsed)
        out[position] = 1.0 if any(f.triggered for f in findings) else 0.0
    return out


# ====================================================================
# WRITERS
# ====================================================================


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")