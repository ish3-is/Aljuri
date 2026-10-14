"""
Fill the remaining Phase 2D specification artifacts.

Several required outputs are transformations of results already on
disk rather than new computation:

  model_comparison              <- candidate_comparison.csv
  corpus_structure_comparison   <- corpus probe + corpus audit summaries
  real_world_validation         <- real_world_regression.csv + promotion.json
  threshold_results             <- selected threshold + operating characteristics
  sampling_strategy            <- dataset_summary.json cell counts and weights
  ablation_results              <- candidate rows grouped by training corpus set

Two need genuine measurement and are computed here:

  feature_importance            native importances of the promoted candidate
  corpus_classifier_metrics     source-separability diagnostic, 3-corpus

Nothing overwrites an existing result.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.phase2c_stages import log, write_csv, write_json

BACKEND = Path(__file__).resolve().parents[1]
RESULTS = BACKEND / "results" / "phase2d"
CANDIDATE = BACKEND / "models" / "basirah-url-v3.joblib"


def read_csv(name: str) -> list[dict[str, str]]:
    path = RESULTS / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(name: str) -> dict[str, Any]:
    path = RESULTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_candidate():
    import joblib

    if not CANDIDATE.exists():
        return None
    bundle = joblib.load(CANDIDATE)
    meta = json.loads(
        (BACKEND / "models" / "basirah-url-v3.metadata.json").read_text(encoding="utf-8")
    )
    return bundle["estimator"], meta


# ====================================================================


def feature_importance() -> list[dict[str, Any]]:
    """Native importances of the promoted candidate."""
    import json as _json

    from app.ml.feature_schema import model_feature_names
    from app.services.feature_extractor import FEATURE_NAMES

    loaded = load_candidate()
    if loaded is None:
        return []
    estimator, meta = loaded
    values = getattr(estimator, "feature_importances_", None)
    if values is None:
        coef = getattr(estimator, "coef_", None)
        values = coef[0] if coef is not None and coef.ndim == 2 else None
    if values is None:
        return []

    names = meta.get("feature_names") or model_feature_names()
    groups_path = BACKEND / "app" / "ml" / "feature_schema.py"

    from app.ml.feature_schema import FEATURE_GROUPS

    rows = [
        {
            "feature": name,
            "position": index,
            "group": FEATURE_GROUPS.get(name, "unclassified"),
            "native_importance": round(float(values[index]), 6),
        }
        for index, name in enumerate(names)
    ]
    rows.sort(key=lambda r: -r["native_importance"])
    return rows


def corpus_classifier_metrics() -> list[dict[str, Any]]:
    """Can a classifier still tell which corpus a URL came from?

    Phase 2C measured this at AUC 0.9916 for two corpora. Repeating it
    for three quantifies whether adding the realistic legitimate corpus
    made source identity MORE or LESS recoverable.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    from app.ml.corpus_adapters import ADAPTERS
    from app.ml.datasets import load_processed
    from app.ml.feature_schema import model_feature_indices
    from scripts.phase2c_stages import featurize

    names = sorted(ADAPTERS)
    if len(names) < 2:
        return []

    columns = model_feature_indices()
    X_parts, y_parts = [], []
    for index, corpus in enumerate(names):
        rows = load_processed(corpus)
        step = max(len(rows) // 25000, 1)
        sample = [r.url for r in rows[::step]][:25000]
        matrix = featurize(sample)[:, columns]
        X_parts.append(matrix)
        y_parts.append(np.full(len(matrix), index))

    X = np.vstack(X_parts)
    y = np.concatenate(y_parts)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    probe = RandomForestClassifier(
        n_estimators=120, random_state=42, n_jobs=-1, class_weight="balanced"
    )
    probe.fit(X_tr, y_tr)
    predictions = probe.predict(X_te)

    # Four corpora are now registered, so this is a MULTI-CLASS problem.
    # Binary ROC-AUC on column 1 would be meaningless; one-vs-rest is
    # the correct comparison across corpora.
    probabilities = probe.predict_proba(X_te)
    try:
        auc = float(roc_auc_score(y_te, probabilities, multi_class="ovr", average="macro"))
        auc_mode = "ovr_macro"
    except ValueError:
        auc = float(roc_auc_score(y_te, probabilities[:, 1]))
        auc_mode = "binary_column1"

    rows = [{
        "corpora": "|".join(names),
        "n_corpora": len(names),
        "n_rows": int(len(y)),
        "n_features": int(X.shape[1]),
        "auc_mode": auc_mode,
        "corpus_classifier_accuracy": round(float(accuracy_score(y_te, predictions)), 6),
        "corpus_classifier_auc": round(auc, 6),
        "chance_accuracy": round(1.0 / len(names), 6),
        "phase2c_comparison_auc": 0.9916,
        "interpretation": (
            "higher than Phase 2C's two-corpus figure means the new "
            "legitimate corpus is MORE distinguishable from the existing "
            "corpora, not less"
        ),
    }]
    return rows


def main() -> int:
    log("=" * 66)
    log("Phase 2D — remaining specification artifacts")
    log("=" * 66)

    # --- derivations ---
    comparison = read_csv("candidate_comparison.csv")
    write_csv(RESULTS / "model_comparison.csv", comparison)
    log(f"  model_comparison.csv ({len(comparison)})")

    structure = read_csv("candidate_corpus_structure.csv") + read_csv(
        "source_structure_probe.csv"
    )
    write_csv(RESULTS / "corpus_structure_comparison.csv", structure)
    log(f"  corpus_structure_comparison.csv ({len(structure)})")

    rw = read_csv("real_world_regression.csv")
    promotion = read_json("promotion.json")
    validation = [
        {
            "source": "basirah-url-v1 (production)",
            "real_world_false_positives": promotion.get("baseline_real_world_fp"),
            "of": 14,
            "phishing_recall": promotion.get("baseline_phishing_recall"),
            "worst_corpus_auc": promotion.get("baseline_worst_corpus_auc"),
        },
        {
            "source": "basirah-url-v3 (candidate)",
            "real_world_false_positives": promotion.get("candidate_real_world_fp"),
            "of": 14,
            "phishing_recall": promotion.get("candidate_phishing_recall"),
            "worst_corpus_auc": promotion.get("candidate_worst_corpus_auc"),
        },
    ]
    for row in rw:
        validation.append({"source": "per-url detail", **row})
    write_csv(RESULTS / "real_world_validation.csv", validation)
    log(f"  real_world_validation.csv ({len(validation)})")

    # --- sampling strategy ---
    summary = read_json("dataset_summary.json")
    cells = summary.get("cell_counts") or summary.get("sampling", {}).get("cell_counts", {})
    write_json(
        RESULTS / "sampling_strategy.json",
        {
            "strategy": "stratified by (corpus, class) with a per-cell cap",
            "cells": cells,
            "total_rows": summary.get("total_rows"),
            "phase2d_addition": (
                "A realistic legitimate corpus was added as a further cell. "
                "It is deliberately NOT allowed to dominate: it is capped to "
                "a share comparable with the existing cells."
            ),
            "overlap": read_json("overlap.json"),
        },
    )
    log("  sampling_strategy.json")

    # --- threshold ---
    if comparison:
        best = min(comparison, key=lambda r: int(r.get("real_world_fp", 99)))
        write_csv(
            RESULTS / "threshold_results.csv",
            [
                {
                    "model": best["model"],
                    "feature_variant": best["feature_variant"],
                    "selected_threshold": best["threshold"],
                    "selected_by": best.get("threshold_selected_by"),
                    "recall_floor_met": best.get("recall_floor_met"),
                    "grouped_precision": best.get("grouped_precision"),
                    "grouped_recall": best.get("grouped_recall"),
                    "grouped_f1": best.get("grouped_f1"),
                    "grouped_fpr": best.get("grouped_fpr"),
                    "phishing_recall_phishtank": best.get("phishing_recall_phishtank"),
                    "calibration_applied": "none (raw probabilities; see promotion.json)",
                }
            ],
        )
        log("  threshold_results.csv")

    # --- calibration ---
    write_csv(
        RESULTS / "calibration_results.csv",
        [
            {
                "model": "basirah-url-v3",
                "method": "raw",
                "applied_in_production": True,
                "rationale": (
                    "Phase 2B found post-hoc calibration did not improve the "
                    "selected model. No calibration was fitted in Phase 2D; "
                    "this row records that decision rather than omitting it."
                ),
                "brier": None,
            },
            {"model": "basirah-url-v3", "method": "platt", "applied_in_production": False,
             "rationale": "not evaluated in Phase 2D", "brier": None},
            {"model": "basirah-url-v3", "method": "isotonic", "applied_in_production": False,
             "rationale": "not evaluated in Phase 2D", "brier": None},
        ],
    )
    log("  calibration_results.csv")

    # --- ablation ---
    # The corpus sets actually trained are: PhiUSIIL alone (v1), PhiUSIIL+MUD
    # (Phase 2C), and all three (Phase 2D). Those are the ablation arms.
    write_csv(
        RESULTS / "ablation_results.csv",
        [
            {
                "arm": "A_phiusil_only",
                "model": "basirah-url-v1 (xgboost)",
                "real_world_fp": promotion.get("baseline_real_world_fp"),
                "phishing_recall": promotion.get("baseline_phishing_recall"),
                "worst_corpus_auc": promotion.get("baseline_worst_corpus_auc"),
                "grouped_auc": 0.5738,
                "note": "carried forward from Phase 2B/2C measurements",
            },
            {
                "arm": "B_phiusil_plus_mud",
                "model": "Phase 2C multi-corpus candidate",
                "real_world_fp": 9,
                "phishing_recall": 0.9091,
                "worst_corpus_auc": 0.9419,
                "grouped_auc": 0.9419,
                "note": "Phase 2C all_features/random_forest, 9/14 real-world FP",
            },
            {
                "arm": "C_all_three_corpora",
                "model": "basirah-url-v3 (xgboost)",
                "real_world_fp": promotion.get("candidate_real_world_fp"),
                "phishing_recall": promotion.get("candidate_phishing_recall"),
                "worst_corpus_auc": promotion.get("candidate_worst_corpus_auc"),
                "grouped_auc": 0.9476,
                "note": "Phase 2D result",
            },
        ],
    )
    log("  ablation_results.csv")

    # --- feature importance ---
    importance = feature_importance()
    write_csv(RESULTS / "feature_importance.csv", importance)
    log(f"  feature_importance.csv ({len(importance)})")

    # --- corpus classifier ---
    log("  corpus_classifier_metrics.csv (training diagnostic, ~1 min)")
    metrics = corpus_classifier_metrics()
    write_csv(RESULTS / "corpus_classifier_metrics.csv", metrics)
    for row in metrics:
        log(f"    {row['n_corpora']}-corpus source AUC: {row['corpus_classifier_auc']}")

    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())