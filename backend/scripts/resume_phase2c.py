"""
Resume Phase 2C from stage 10.

The 16-model feature-variant sweep is expensive (~35 minutes) and its
results are already on disk in `feature_variant_comparison.csv`. This
script rebuilds the fitted models for the variants that the remaining
stages need, then runs stages 10-15 — leave-one-corpus-out, semantic
regression, heuristics, fusion and the v2 promotion decision.

Reuses the recorded thresholds so the numbers stay identical to the
original run rather than being silently re-tuned.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.datasets import AuditedRow
from app.ml.experiment import build_models, compute_metrics, model_file_size_mb, timed_probabilities
from app.ml.feature_schema import model_feature_indices, model_feature_names
from app.ml.feature_stability import analyse as analyse_stability
from app.ml.semantic_cases import ALL_CASES, LEGITIMATE_CASES, REAL_WORLD_LEGITIMATE
from scripts.phase2c_stages import (
    evaluate_semantic_cases,
    featurize,
    heuristic_analysis,
    heuristic_risk_column,
    log,
    real_world_regression,
    write_csv,
    write_json,
)
from scripts.run_phase2c_experiment import (
    BACKEND,
    FEATURE_VARIANTS,
    MODELS,
    RESULTS,
    _best_key,
    _decide_promotion,
    _finalize,
)
from app.ml.feature_stability import Stability, indices_for

RANDOM_STATE = 42


def main() -> int:
    started = time.perf_counter()
    started_time = time.perf_counter()
    RESULTS.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("Phase 2C RESUME — stages 10-15, reusing the recorded variant sweep")
    log("=" * 70)

    variant_csv = RESULTS / "feature_variant_comparison.csv"
    if not variant_csv.exists():
        log("No feature_variant_comparison.csv — run the full experiment first.")
        return 1
    variant_rows = list(csv.DictReader(variant_csv.open(encoding="utf-8")))
    log(f"  loaded {len(variant_rows)} recorded model results")

    # ---- rebuild dataset + features (identical construction) ----
    log("  rebuilding multi-corpus dataset")
    from app.ml.corpus_adapters import semantics_summary
    from app.ml.corpus_quality import gate_corpus
    from app.ml.datasets import load_processed
    from app.ml.multi_corpus import build as build_multi_corpus
    from app.ml.multi_corpus import measure_overlap
    from app.services.feature_extractor import FEATURE_NAMES

    # Use the CACHED processed rows, not a fresh adapter pass.
    #
    # The adapters re-read the raw files and produce 366,808 rows, while
    # the cached cleaned corpora hold 366,400 (cross-corpus duplicate
    # URLs were dropped in an earlier pass). That 408-row difference
    # changes the domain split, which would silently invalidate the
    # thresholds reused from the recorded sweep. Reproducing the original
    # split exactly requires reproducing its inputs exactly.
    per_corpus: dict[str, list[AuditedRow]] = {}
    contexts: dict[str, dict[str, Any]] = {}
    gate_reports = {}
    from app.ml.corpus_adapters import ADAPTERS

    for name in sorted(ADAPTERS):
        rows = load_processed(name)
        per_corpus[name] = rows
        adapter = ADAPTERS[name]()
        contexts[name] = adapter.context()
        gate_reports[name] = gate_corpus(name, rows, **contexts[name])
        log(f"    {name:9} rows={len(rows):,} (cached)")

    overlap = measure_overlap(per_corpus)
    dataset = build_multi_corpus(per_corpus)

    X = featurize([r.url for r in dataset.rows], label="multi-corpus")
    y = dataset.label_array()
    groups = dataset.groups()
    corpora = dataset.corpus_array()

    # ---- same grouped split as the main run ----
    domains = np.asarray(sorted(set(groups)))
    rng = np.random.default_rng(RANDOM_STATE)
    shuffled = rng.permutation(len(domains))
    test_domains = {domains[i] for i in shuffled[: int(len(domains) * 0.20)]}
    is_test = np.isin(groups, list(test_domains))
    holdout_idx = np.where(is_test)[0]
    train_idx = np.where(~is_test)[0]
    leakage = {
        "intersection_train_holdout_domains": len(set(groups[train_idx]) & set(groups[holdout_idx])),
        "is_empty": not (set(groups[train_idx]) & set(groups[holdout_idx])),
        "train_rows": int(len(train_idx)),
        "holdout_rows": int(len(holdout_idx)),
        "train_phishing_rate": round(float(y[train_idx].mean()), 4),
        "holdout_phishing_rate": round(float(y[holdout_idx].mean()), 4),
    }
    log(f"  split: train={len(train_idx):,} holdout={len(holdout_idx):,} leak={leakage['is_empty']}")

    corpus_holdout: dict[str, np.ndarray] = {}
    from sklearn.model_selection import StratifiedGroupKFold

    for corpus in sorted(per_corpus):
        idx = np.where(corpora == corpus)[0]
        sp = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
        _, hold = next(sp.split(np.zeros(len(idx)), y[idx], groups[idx]))
        corpus_holdout[corpus] = idx[hold]

    # ---- stability + variant columns (same computation) ----
    per_corpus_X, per_corpus_y = {}, {}
    for corpus in sorted(per_corpus):
        mask = corpora == corpus
        per_corpus_X[corpus] = X[mask]
        per_corpus_y[corpus] = y[mask]
    stability = analyse_stability(FEATURE_NAMES, per_corpus_X, per_corpus_y)
    from app.ml.feature_stability import counts_by_class

    stability_counts = counts_by_class(stability)

    base_cols = model_feature_indices()
    base_set = set(base_cols)
    variant_columns: dict[str, list[int]] = {}
    for name, categories in FEATURE_VARIANTS.items():
        if categories is None:
            variant_columns[name] = list(base_cols)
        else:
            positions = indices_for(FEATURE_NAMES, stability, categories)
            variant_columns[name] = [i for i in positions if i in base_set]

    # ---- refit only what the remaining stages need ----
    best_key = _best_key(variant_rows)
    variant_name, model_name = best_key.split("|")
    log(f"  best configuration: {best_key}")
    cols = variant_columns[variant_name]
    log(f"  refitting {model_name} [{variant_name}] on {len(train_idx):,} rows")

    estimator = build_models()[model_name]()
    estimator.fit(X[train_idx][:, cols], y[train_idx])

    # Reuse the threshold recorded by the original sweep so results match.
    threshold = float(
        next(
            r["threshold"] for r in variant_rows
            if r["feature_variant"] == variant_name and r["model"] == model_name
        )
    )
    log(f"  threshold (from recorded sweep): {threshold:.6f}")

    fitted = {best_key: (estimator, cols, threshold)}
    thresholds = {best_key: threshold}

    return _finalize(
        started=started_time,
        dataset=dataset,
        multi_X=X,
        y=y,
        multi_groups=groups,
        multi_corpora=corpora,
        per_corpus_X=per_corpus_X,
        per_corpus_y=per_corpus_y,
        stability=stability,
        stability_counts=stability_counts,
        variant_columns=variant_columns,
        variant_rows=variant_rows,
        comparison_rows=[],
        loco_rows=[],
        fitted=fitted,
        thresholds=thresholds,
        overlap=overlap,
        gate_reports=gate_reports,
        contexts=contexts,
        train_idx=train_idx,
        holdout_idx=holdout_idx,
        corpus_holdout=corpus_holdout,
        leakage=leakage,
        source_bias_all=json.loads((RESULTS / "corpus_classifier_metrics.json").read_text(encoding="utf-8"))["all_features"],
        source_bias_stable=json.loads((RESULTS / "corpus_classifier_metrics.json").read_text(encoding="utf-8"))["stable_only"],
    )


if __name__ == "__main__":
    raise SystemExit(main())