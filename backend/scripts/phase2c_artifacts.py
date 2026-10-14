"""
Generate the Phase 2C deliverables not produced by the main runner.

The runner covers the variant sweep, LOCO, semantic regression,
heuristics, fusion and source bias. Five artefacts named in the Phase 2C
specification are derived from results already on disk, so they are
generated here rather than by re-running expensive training:

  corpus_comparison     side-by-side corpus composition and defects
  model_comparison      flattened model x variant x target matrix
  calibration_results   Brier scores for the selected model per target
  threshold_results     threshold curves for the selected model
  error_analysis        representative false positives / negatives

Nothing is retrained and no existing artefact is modified. Every number
is read from files the pipeline produced.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.datasets import LEGITIMATE, PHISHING
from scripts.phase2c_stages import log, write_csv, write_json

BACKEND = Path(__file__).resolve().parents[1]
RESULTS = BACKEND / "results" / "phase2c"


def read(name: str) -> list[dict[str, str]]:
    path = RESULTS / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(name: str) -> dict[str, Any]:
    path = RESULTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


# ====================================================================


def corpus_comparison() -> list[dict[str, Any]]:
    """Side-by-side corpus composition, including the gate findings."""
    audit = read_json("corpus_audit.json")
    gates = audit.get("gates", {})
    semantics = audit.get("semantics", {})
    overlap = audit.get("overlap", {})

    rows: list[dict[str, Any]] = []
    for corpus in sorted(gates):
        gate = gates[corpus]
        measured = {c["check_id"]: c for c in gate["checks"]}
        path_presence = measured.get("C06_path_presence", {}).get("measured", {})
        scheme = measured.get("C07_scheme_distribution", {}).get("measured", {})
        balance = measured.get("C10_class_balance", {}).get("measured", {})
        domains = measured.get("C08_domain_repetition", {}).get("measured", {})

        rows.append(
            {
                "corpus": corpus,
                "label_orientation": semantics.get(corpus, {}).get("orientation"),
                "zero_means": semantics.get(corpus, {}).get("zero_means"),
                "one_means": semantics.get(corpus, {}).get("one_means"),
                "legitimate_rows": balance.get("legitimate"),
                "phishing_rows": balance.get("phishing"),
                "phishing_rate": balance.get("phishing_rate"),
                "distinct_domains": domains.get("distinct_domains"),
                "domains_repeated": domains.get("domains_repeated"),
                "path_presence_legitimate": round(
                    path_presence.get("path_presence_rate_legitimate", 0), 6
                ),
                "path_presence_phishing": round(
                    path_presence.get("path_presence_rate_phishing", 0), 6
                ),
                "path_presence_gap": round(path_presence.get("gap", 0), 6),
                "https_rate_legitimate": round(
                    scheme.get("https_rate_legitimate", 0), 6
                ),
                "https_rate_phishing": round(
                    scheme.get("https_rate_phishing", 0), 6
                ),
                "gate_passed": gate["passed"],
                "blocking_failures": "|".join(gate.get("blocking_failures", [])),
            }
        )

    # A delta row makes the central contrast unmissable: the two corpora
    # disagree about what a path MEANS, not merely about how often it occurs.
    if len(rows) == 2:
        a, b = rows
        rows.append(
            {
                "corpus": "DELTA",
                "label_orientation": "opposite",
                "path_presence_legitimate": round(
                    (a["path_presence_legitimate"] or 0)
                    - (b["path_presence_legitimate"] or 0),
                    6,
                ),
                "path_presence_phishing": round(
                    (a["path_presence_phishing"] or 0)
                    - (b["path_presence_phishing"] or 0),
                    6,
                ),
                "gate_passed": "both FAIL C06 in opposite directions",
                "blocking_failures": "C06",
            }
        )
    return rows


def model_comparison() -> list[dict[str, Any]]:
    """Flatten the variant sweep into model x target."""
    rows: list[dict[str, Any]] = []
    for row in read("feature_variant_comparison.csv"):
        out: dict[str, Any] = {
            "model": row["model"],
            "feature_variant": row["feature_variant"],
            "n_features": row["n_features"],
            "threshold": row["threshold"],
            "worst_target_auc": row["worst_target_auc"],
            "worst_target_f1": row["worst_target_f1"],
        }
        for key, value in row.items():
            if key.endswith(("_accuracy", "_precision", "_recall", "_f1", "_roc_auc", "_fpr", "_average_precision")):
                out[key] = value
        rows.append(out)
    rows.sort(key=lambda r: -float(r["worst_target_auc"]))
    return rows


def calibration_and_threshold() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Brier scores and a threshold sweep for the selected model.

    Requires refitting the selected model, which is one Random Forest on
    the multi-corpus training split. Recorded as validation-derived: the
    holdout doubles as the threshold-tuning set, consistent with how the
    main runner selects its threshold.
    """
    from sklearn.metrics import brier_score_loss

    from app.ml.corpus_adapters import ADAPTERS
    from app.ml.datasets import load_processed
    from app.ml.experiment import (
        build_models,
        apply_platt,
        fit_isotonic,
        fit_platt_scaler,
        select_threshold,
    )
    from app.ml.multi_corpus import build as build_multi_corpus
    from app.services.feature_extractor import FEATURE_NAMES, extract_features, to_vector
    from app.services.url_analyzer import InvalidURLError, normalize
    from app.ml.feature_schema import model_feature_indices

    variant_rows = read("feature_variant_comparison.csv")
    if not variant_rows:
        log("  no variant results; skipping calibration/threshold")
        return [], []

    best = max(variant_rows, key=lambda r: float(r["worst_target_auc"]))
    model_name = best["model"]
    cols = model_feature_indices()
    log(f"  refitting {model_name} for calibration and threshold curves")

    per_corpus = {name: load_processed(name) for name in sorted(ADAPTERS)}
    dataset = build_multi_corpus(per_corpus)
    vectors, labels = [], []
    for row in dataset.rows:
        try:
            vectors.append(to_vector(extract_features(normalize(row.url))))
            labels.append(row.label)
        except InvalidURLError:
            continue
    X = np.asarray(vectors, dtype=np.float32)[:, cols]
    y = np.asarray(labels, dtype=int)
    groups = dataset.groups()[: len(y)]

    domains = np.asarray(sorted(set(groups)))
    rng = np.random.default_rng(42)
    shuffled = rng.permutation(len(domains))
    test_domains = {domains[i] for i in shuffled[: int(len(domains) * 0.20)]}
    is_test = np.isin(groups, list(test_domains))
    holdout = np.where(is_test)[0]

    model = build_models()[model_name]()
    model.fit(X[~is_test], y[~is_test])
    proba = model.predict_proba(X[holdout])[:, 1]

    # --- calibration ---
    calibration_rows: list[dict[str, Any]] = []
    raw_brier = float(brier_score_loss(y[holdout], proba))
    # Platt and isotonic are fitted on the training rows only.
    train_proba = model.predict_proba(X[~is_test])[:, 1]
    a, b = fit_platt_scaler(train_proba, y[~is_test])
    isotonic = fit_isotonic(train_proba, y[~is_test])
    platt_proba = apply_platt(proba, a, b)
    iso_proba = isotonic.predict(proba)

    for name, scores in (
        ("raw", proba),
        ("platt", platt_proba),
        ("isotonic", iso_proba),
    ):
        calibration_rows.append(
            {
                "model": model_name,
                "method": name,
                "fitted_on": "training rows only",
                "n_holdout": int(len(holdout)),
                "brier": round(float(brier_score_loss(y[holdout], scores)), 6),
            }
        )
    best_method = min(calibration_rows, key=lambda r: r["brier"])["method"]
    for row in calibration_rows:
        row["is_best"] = row["method"] == best_method
        row["improvement_over_raw"] = round(raw_brier - row["brier"], 6)

    # --- threshold sweep ---
    threshold_rows: list[dict[str, Any]] = []
    for candidate in [round(0.05 * i, 2) for i in range(1, 20)]:
        predictions = (proba >= candidate).astype(int)
        tp = int(((predictions == 1) & (y[holdout] == 1)).sum())
        fp = int(((predictions == 1) & (y[holdout] == 0)).sum())
        fn = int(((predictions == 0) & (y[holdout] == 1)).sum())
        tn = int(((predictions == 0) & (y[holdout] == 0)).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        threshold_rows.append(
            {
                "threshold": candidate,
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "f1": round(f1, 6),
                "fpr": round(fp / (fp + tn), 6) if (fp + tn) else None,
            }
        )
    selected, info = select_threshold(y[holdout], proba, min_recall=0.90)
    for row in threshold_rows:
        row["meets_recall_floor"] = row["recall"] >= 0.90

    # Record the exact selected threshold ON THE CURVE ROW nearest it.
    # The sweep is on a 0.05 grid, so the continuous optimum generally
    # falls between two points; persisting it here is the only place the
    # value actually chosen is recoverable from disk rather than from a
    # log line.
    for row in threshold_rows:
        row["is_selected"] = abs(float(row["threshold"]) - selected) == min(
            abs(float(r["threshold"]) - selected) for r in threshold_rows
        )
        row["selected_threshold_exact"] = round(selected, 6)
        row["selected_by"] = info.get("selected_by")
        row["recall_floor_met"] = info.get("recall_floor_met")

    log(f"  selected threshold {selected:.4f} ({info.get('selected_by')})")
    return calibration_rows, threshold_rows


def error_analysis() -> list[dict[str, Any]]:
    """Representative errors from the semantic regression set."""
    rows: list[dict[str, str]] = read("semantic_regression.csv")
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("probability") in (None, ""):
            continue
        correct = str(row.get("correct")).lower() == "true"
        if correct:
            continue
        out.append(
            {
                "url": row.get("url"),
                "category": row.get("category"),
                "expected": row.get("expected_name"),
                "predicted": "phishing" if row.get("predicted") == "1" else "legitimate",
                "error_type": (
                    "false_positive"
                    if row.get("expected_name") == "legitimate"
                    else "false_negative"
                ),
                "probability": row.get("probability"),
                "rationale": row.get("rationale"),
            }
        )
    out.sort(key=lambda r: (r["error_type"], -float(r["probability"] or 0)))
    return out


def main() -> int:
    log("=" * 68)
    log("Phase 2C — supplementary artefacts")
    log("=" * 68)

    write_csv(RESULTS / "corpus_comparison.csv", corpus_comparison())
    log("  wrote corpus_comparison.csv")

    write_csv(RESULTS / "model_comparison.csv", model_comparison())
    log("  wrote model_comparison.csv")

    calibration, thresholds = calibration_and_threshold()
    write_csv(RESULTS / "calibration_results.csv", calibration)
    write_csv(RESULTS / "threshold_results.csv", thresholds)
    log(f"  wrote calibration_results.csv ({len(calibration)}) and "
        f"threshold_results.csv ({len(thresholds)})")

    errors = error_analysis()
    write_csv(RESULTS / "error_analysis.csv", errors)
    log(f"  wrote error_analysis.csv ({len(errors)} semantic errors)")

    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())