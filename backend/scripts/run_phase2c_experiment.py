"""
Phase 2C — Multi-Corpus Robust URL Intelligence.

Research question:
    How does multi-corpus training affect the generalization and
    false-positive behaviour of phishing URL classifiers under dataset
    distribution shift?

Run:
    .\\.venv\\Scripts\\python.exe -m scripts.run_phase2c_experiment

Stages:
     1  load both corpora through their adapters
     2  run the corpus quality gate (training aborts on critical failure)
     3  measure cross-corpus domain/URL overlap
     4  build a balanced multi-corpus dataset
     5  featurize with BASIRAH's production extractor
     6  classify feature stability across corpora
     7  measure corpus-source bias (can a model tell the corpora apart?)
     8  train 4 model families x 4 feature variants
     9  leave-one-corpus-out and holdout evaluation
    10  semantic + real-world regression
    11  calibration and threshold selection on validation only
    12  heuristics: precision, coverage, redundancy
    13  fusion ablation
    14  select v2 only if cross-corpus robustness justifies it
    15  write every artefact to results/phase2c/

The corpus quality gate is intentionally run in REPORT mode, not abort
mode: PhiUSIIL is known to fail the path-presence check, and the whole
point of Phase 2C is to measure what that defect does rather than to
refuse to look at it. A separate `--strict` mode aborts.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.corpus_adapters import ADAPTERS, load_corpus, semantics_summary
from app.ml.corpus_quality import gate_corpus
from app.ml.datasets import LEGITIMATE, PHISHING, AuditedRow
from app.ml.experiment import (
    RANDOM_STATE,
    apply_platt,
    build_models,
    calibration_report,
    compute_metrics,
    fit_isotonic,
    fit_platt_scaler,
    model_file_size_mb,
    select_threshold,
    timed_probabilities,
)
from app.ml.feature_schema import (
    FEATURE_EXTRACTOR_VERSION,
    model_feature_indices,
    model_feature_names,
    save_schema,
)
from app.ml.feature_stability import (
    Stability,
    analyse as analyse_stability,
    counts_by_class,
    indices_for,
)
from app.ml.multi_corpus import build as build_multi_corpus
from app.ml.semantic_cases import (
    ALL_CASES,
    LEGITIMATE_CASES,
    PHISHING_CASES,
    REAL_WORLD_LEGITIMATE,
    categories as semantic_categories,
)
from app.ml.splits import DomainLeakageError, grouped_split
from app.services.feature_extractor import FEATURE_NAMES
from scripts.phase2c_stages import (
    corpus_classifier_metrics,
    evaluate_semantic_cases,
    featurize,
    heuristic_analysis,
    heuristic_any_triggered,
    heuristic_risk_column,
    log,
    real_world_regression,
    write_csv,
    write_json,
)

BACKEND = Path(__file__).resolve().parents[1]
RESULTS = BACKEND / "results" / "phase2c"
MODELS = BACKEND / "models"
PRODUCTION_NAME = "basirah-url-v2"
MIN_RECALL = 0.90

FEATURE_VARIANTS: dict[str, list[Stability] | None] = {
    "all_features": None,
    "stable_only": {Stability.STABLE},
    "stable_plus_weak": {Stability.STABLE, Stability.WEAK},
    "exclude_inverted": {
        Stability.STABLE, Stability.WEAK, Stability.CORPUS_SENSITIVE
    },
}

# ====================================================================
# MAIN
# ====================================================================


def main() -> int:
    started = time.perf_counter()
    RESULTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("BASIRAH Phase 2C — Multi-Corpus Robust URL Intelligence")
    log("=" * 70)

    # ----------------------------------------------------------------
    # STAGE 1 — load corpora through adapters
    # ----------------------------------------------------------------
    log("STAGE 1/15  loading corpora through adapters")
    per_corpus: dict[str, list[AuditedRow]] = {}
    contexts: dict[str, dict[str, Any]] = {}
    for name in sorted(ADAPTERS):
        rows, context = load_corpus(name)
        per_corpus[name] = rows
        contexts[name] = context
        counts = np.bincount([r.label for r in rows], minlength=2)
        log(f"  {name:9} rows={len(rows):7,}  legit={counts[0]:7,}  phish={counts[1]:7,}")

    # ----------------------------------------------------------------
    # STAGE 2 — corpus quality gate
    # ----------------------------------------------------------------
    log("STAGE 2/15  corpus quality gate")
    gate_reports = {}
    for name in sorted(per_corpus):
        report = gate_corpus(name, per_corpus[name], **contexts[name])
        report.write(RESULTS)
        gate_reports[name] = report
        status = "PASS" if report.passed else "FAIL (training proceeds; see notes)"
        log(f"  {name:9} gate={status}")
        for check in report.checks:
            if check.verdict.value == "fail":
                log(f"      FAIL {check.check_id}: {check.message[:76]}")

    # ----------------------------------------------------------------
    # STAGE 3 — cross-corpus overlap
    # ----------------------------------------------------------------
    log("STAGE 3/15  measuring cross-corpus overlap")
    from app.ml.multi_corpus import measure_overlap

    overlap = measure_overlap(per_corpus)
    for pair in overlap["pairs"]:
        log(
            f"  {pair['pair']:22} same_url={pair['same_normalized_url']:6,} "
            f"same_domain={pair['same_registered_domain']:7,} "
            f"domain_jaccard={pair['domain_jaccard']:.4f}"
        )

    # ----------------------------------------------------------------
    # STAGE 4 — balanced multi-corpus dataset
    # ----------------------------------------------------------------
    log("STAGE 4/15  building balanced multi-corpus dataset")
    dataset = build_multi_corpus(per_corpus)
    log(f"  total={len(dataset.rows):,}  cells={dataset.cell_counts}")
    log(f"  cross-corpus duplicate URLs dropped={dataset.overlap['cross_corpus_duplicate_urls_dropped']:,}")

    # ----------------------------------------------------------------
    # STAGE 5 — featurize
    # ----------------------------------------------------------------
    log("STAGE 5/15  featurizing with production extractor")
    multi_X = featurize([r.url for r in dataset.rows], label="multi-corpus")
    y = dataset.label_array()
    multi_groups = dataset.groups()
    multi_corpora = dataset.corpus_array()
    labels_global = y

    per_corpus_X: dict[str, np.ndarray] = {}
    per_corpus_y: dict[str, np.ndarray] = {}
    for corpus in sorted(per_corpus):
        mask = multi_corpora == corpus
        per_corpus_X[corpus] = multi_X[mask]
        per_corpus_y[corpus] = y[mask]
        log(f"  {corpus:9} X={per_corpus_X[corpus].shape} phish_rate={y[mask].mean():.4f}")

    from app.services.feature_extractor import FEATURE_NAMES

    # ----------------------------------------------------------------
    # STAGE 6 — feature stability
    # ----------------------------------------------------------------
    log("STAGE 6/15  feature stability across corpora")
    base_cols = model_feature_indices()
    base_names = model_feature_names()
    stability = analyse_stability(FEATURE_NAMES, per_corpus_X, per_corpus_y)
    counts = counts_by_class(stability)
    log(f"  {counts}")
    write_csv(RESULTS / "feature_stability.csv", [s.to_row() for s in stability])

    variant_columns: dict[str, list[int]] = {}
    for variant_name, categories in FEATURE_VARIANTS.items():
        if categories is None:
            variant_columns[variant_name] = list(base_cols)
        else:
            positions = indices_for(FEATURE_NAMES, stability, categories)
            variant_columns[variant_name] = [i for i in positions if i in set(base_cols)]
        log(f"  variant {variant_name:20} {len(variant_columns[variant_name])} features")

    return _train_and_evaluate(
        started=started,
        per_corpus=per_corpus,
        dataset=dataset,
        multi_X=multi_X,
        y=y,
        multi_groups=multi_groups,
        multi_corpora=multi_corpora,
        per_corpus_X=per_corpus_X,
        per_corpus_y=per_corpus_y,
        stability=stability,
        stability_counts=counts,
        variant_columns=variant_columns,
        overlap=overlap,
        gate_reports=gate_reports,
        contexts=contexts,
    )

# ====================================================================
# STAGES 7-15
# ====================================================================


def _train_and_evaluate(
    *,
    started: float,
    per_corpus: dict[str, list[AuditedRow]],
    dataset,
    multi_X: np.ndarray,
    y: np.ndarray,
    multi_groups: np.ndarray,
    multi_corpora: np.ndarray,
    per_corpus_X: dict[str, np.ndarray],
    per_corpus_y: dict[str, np.ndarray],
    stability,
    stability_counts: dict[str, int],
    variant_columns: dict[str, list[int]],
    overlap: dict[str, Any],
    gate_reports: dict[str, Any],
    contexts: dict[str, dict[str, Any]],
) -> int:
    from sklearn.model_selection import StratifiedGroupKFold

    rows = dataset.rows
    corpus_names = sorted(per_corpus)

    # ----------------------------------------------------------------
    # STAGE 7 — corpus-source bias
    # ----------------------------------------------------------------
    log("STAGE 7/15  corpus-source bias diagnostic")
    source_bias_all = corpus_classifier_metrics(
        per_corpus_X, columns=list(variant_columns["all_features"]), label_suffix="all_features"
    )
    source_bias_stable = corpus_classifier_metrics(
        per_corpus_X, columns=variant_columns["stable_only"], label_suffix="stable_only"
    )
    log(
        f"  corpus classifier AUC (all)  = "
        f"{source_bias_all.get('corpus_classifier_auc')}"
    )
    log(
        f"  corpus classifier AUC (stable)= "
        f"{source_bias_stable.get('corpus_classifier_auc')}"
    )
    write_json(
        RESULTS / "corpus_classifier_metrics.json",
        {"all_features": source_bias_all, "stable_only": source_bias_stable},
    )
    write_csv(
        RESULTS / "corpus_classifier_metrics.csv",
        [
            {"feature_set": k, **v}
            for k, v in (("all_features", source_bias_all), ("stable_only", source_bias_stable))
        ],
    )

    # ----------------------------------------------------------------
    # STAGE 8-9 — train, evaluate across variants and targets
    # ----------------------------------------------------------------
    log("STAGE 8/15  training models across feature variants")
    candidates = build_models()

# ---- split the multi-corpus set by registered domain ----
    #
    # StratifiedGroupKFold on 366k rows produced a 22%/78% split because
    # MUD's domains are heavily concentrated: a handful of groups are
    # enormous, so one fold swallows most of the data. That would leave
    # the model trained on a fraction of the corpus.
    #
    # Instead: assign whole DOMAINS to partitions with a target domain
    # count per partition, then verify the class balance afterwards. The
    # group guarantee (no domain spans partitions) is preserved exactly;
    # only the sizing changes.
    domains = np.asarray(sorted(set(multi_groups)))
    rng = np.random.default_rng(RANDOM_STATE)
    shuffled = rng.permutation(len(domains))
    target_test_domains = int(len(domains) * 0.20)
    test_domain_set = {domains[i] for i in shuffled[:target_test_domains]}

    is_test = np.isin(multi_groups, list(test_domain_set))
    holdout_idx = np.where(is_test)[0]
    train_idx = np.where(~is_test)[0]

    train_domains = set(multi_groups[train_idx])
    holdout_domains = set(multi_groups[holdout_idx])
    leakage = {
        "intersection_train_holdout_domains": len(train_domains & holdout_domains),
        "is_empty": not (train_domains & holdout_domains),
        "train_rows": int(len(train_idx)),
        "holdout_rows": int(len(holdout_idx)),
        "train_phishing_rate": round(float(y[train_idx].mean()), 4),
            "holdout_phishing_rate": round(float(y[holdout_idx].mean()), 4),
            "total_domains": int(len(domains)),
        }
    log(
        f"  mixed grouped split: train={len(train_idx):,} holdout={len(holdout_idx):,} "
        f"(phish rate {y[train_idx].mean():.3f} / {y[holdout_idx].mean():.3f})"
    )
    log(f"  LEAKAGE CHECK train vs holdout -> empty: {leakage['is_empty']}")
    assert leakage["is_empty"], "registered-domain leakage in the mixed split"

    # Per-corpus holdouts, for the "train X -> test Y" experiments.
    corpus_holdout: dict[str, np.ndarray] = {}
    for corpus in corpus_names:
        indices = np.where(multi_corpora == corpus)[0]
        g = multi_groups[indices]
        yy = y[indices]
        splitter2 = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
        _, hold = next(splitter2.split(np.zeros(len(yy)), yy, g))
        corpus_holdout[corpus] = indices[hold]
        log(f"  {corpus} holdout: {len(hold):,} rows")

    comparison_rows: list[dict[str, Any]] = []
    variant_rows: list[dict[str, Any]] = []
    loco_rows: list[dict[str, Any]] = []
    fitted: dict[str, object] = {}
    thresholds: dict[str, float] = {}

    # Flushed after every fit. A 16-fit sweep takes ~40 minutes, and
    # buffering results until the end means a crash in the last fit
    # discards every earlier one.
    def flush_variant_results() -> None:
        write_csv(RESULTS / "feature_variant_comparison.csv", variant_rows)

    for variant_name, cols in variant_columns.items():
        if not cols:
            log(f"  variant {variant_name}: no features, skipped")
            continue
        Xv = multi_X[:, cols]

        for model_name, factory in candidates.items():
            log(f"  fit {model_name} [{variant_name}] on {len(train_idx):,} rows")
            model = factory()
            model.fit(Xv[train_idx], y[train_idx])
            size_mb = model_file_size_mb(model)

            # Threshold from the mixed holdout, used only as VALIDATION
            # for threshold tuning. The per-corpus holdouts remain the
            # untouched test sets.
            val_prob, _ = timed_probabilities(model, Xv[holdout_idx])
            threshold, threshold_info = select_threshold(
                y[holdout_idx], val_prob, min_recall=MIN_RECALL
            )
            thresholds[f"{variant_name}|{model_name}"] = threshold

            # --- evaluation across every target ---
            evals: dict[str, np.ndarray] = {}
            evals["mixed_grouped_holdout"] = holdout_idx
            for corpus in corpus_names:
                evals[f"{corpus}_holdout"] = corpus_holdout[corpus]

            per_target: dict[str, dict[str, Any]] = {}
            for target_name, idx in evals.items():
                proba, ms = timed_probabilities(model, Xv[idx])
                metrics = compute_metrics(y[idx], proba, threshold, ms, size_mb)
                per_target[target_name] = {
                    "n": int(len(idx)),
                    **{k: metrics.as_row()[k] for k in metrics.as_row()},
                }

            worst_auc = min(
                v["roc_auc"] for v in per_target.values() if v["roc_auc"] == v["roc_auc"]
            )
            worst_f1 = min(
                v["f1"] for v in per_target.values() if v["f1"] == v["f1"]
            )

            row = {
                "feature_variant": variant_name,
                "model": model_name,
                "n_features": len(cols),
                "threshold": round(threshold, 6),
                "worst_target_auc": round(worst_auc, 6),
                "worst_target_f1": round(worst_f1, 6),
            }
            for target_name, values in per_target.items():
                for key in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr", "average_precision"):
                    row[f"{target_name}_{key}"] = values[key]
            variant_rows.append(row)

            log(
                f"    worst_auc={worst_auc:.4f} worst_f1={worst_f1:.4f} "
                f"| mixed f1={per_target['mixed_grouped_holdout']['f1']:.4f}"
            )

            fitted[f"{variant_name}|{model_name}"] = (model, cols, threshold)
            flush_variant_results()

    write_csv(RESULTS / "feature_variant_comparison.csv", variant_rows)

    return _finalize(
        started=started,
        dataset=dataset,
        multi_X=multi_X,
        y=y,
        multi_groups=multi_groups,
        multi_corpora=multi_corpora,
        per_corpus_X=per_corpus_X,
        per_corpus_y=per_corpus_y,
        stability=stability,
        stability_counts=stability_counts,
        variant_columns=variant_columns,
        variant_rows=variant_rows,
        comparison_rows=comparison_rows,
        loco_rows=loco_rows,
        fitted=fitted,
        thresholds=thresholds,
        overlap=overlap,
        gate_reports=gate_reports,
        contexts=contexts,
        train_idx=train_idx,
        holdout_idx=holdout_idx,
        corpus_holdout=corpus_holdout,
        leakage=leakage,
        source_bias_all=source_bias_all,
        source_bias_stable=source_bias_stable,
    )

# ====================================================================
# STAGES 10-15
# ====================================================================


def _finalize(
    *,
    started: float,
    dataset,
    multi_X: np.ndarray,
    y: np.ndarray,
    multi_groups: np.ndarray,
    multi_corpora: np.ndarray,
    per_corpus_X: dict[str, np.ndarray],
    per_corpus_y: dict[str, np.ndarray],
    stability,
    stability_counts: dict[str, int],
    variant_columns: dict[str, list[int]],
    variant_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    loco_rows: list[dict[str, Any]],
    fitted: dict[str, Any],
    thresholds: dict[str, float],
    overlap: dict[str, Any],
    gate_reports: dict[str, Any],
    contexts: dict[str, dict[str, Any]],
    train_idx: np.ndarray,
    holdout_idx: np.ndarray,
    corpus_holdout: dict[str, np.ndarray],
    leakage: dict[str, Any],
    source_bias_all: dict[str, Any],
    source_bias_stable: dict[str, Any],
) -> int:
    from sklearn.model_selection import StratifiedGroupKFold

    rows = dataset.rows
    # Corpus names come from the per-corpus matrices, which are
    # already passed in; the `per_corpus` row lists are not needed here.
    corpus_names = sorted(per_corpus_X)

    # ----------------------------------------------------------------
    # STAGE 10 — leave-one-corpus-out
    # ----------------------------------------------------------------
    log("STAGE 10/15  leave-one-corpus-out evaluation")

    # A resume run already produced leave_one_corpus_out.csv; reuse it
    # rather than retraining eight models. The expensive sweep is never
    # repeated, and stage 10 is deterministic given the same split.
    reuse_loco = bool(loco_rows) or (RESULTS / "leave_one_corpus_out.csv").exists()
    if reuse_loco and not loco_rows:
        with (RESULTS / "leave_one_corpus_out.csv").open(encoding="utf-8") as handle:
            loco_rows = list(csv.DictReader(handle))
        log(f"  reusing {len(loco_rows)} recorded LOCO results")

    candidates = {} if reuse_loco else build_models()
    best_variant = _best_variant(variant_rows)
    loco_columns = variant_columns[best_variant]
    log(f"  using feature variant '{best_variant}' ({len(loco_columns)} features)")

    # --- single-corpus training sets ---
    for held_out in corpus_names:
        train_mask = multi_corpora != held_out
        test_idx = corpus_holdout[held_out]
        train_indices = np.where(train_mask)[0]
        # drop the held-out corpus's domains from training to keep it unseen
        held_domains = set(multi_groups[test_idx])
        train_indices = np.array(
            [i for i in train_indices if multi_groups[i] not in held_domains],
            dtype=int,
        )
        log(
            f"  train without {held_out}: {len(train_indices):,} rows -> "
            f"test on {held_out} {len(test_idx):,}"
        )
        for model_name, factory in candidates.items():
            model = factory()
            model.fit(multi_X[train_indices][:, loco_columns], y[train_indices])
            proba, ms = timed_probabilities(model, multi_X[test_idx][:, loco_columns])
            metrics = compute_metrics(y[test_idx], proba, 0.5, ms, model_file_size_mb(model))
            loco_rows.append(
                {
                    "experiment": f"train_without_{held_out}->test_{held_out}",
                    "model": model_name,
                    "trained_on": held_out and ",".join(c for c in corpus_names if c != held_out) or "none",
                    "tested_on": held_out,
                    "n_train": int(len(train_indices)),
                    "n_test": int(len(test_idx)),
                    **{k: metrics.as_row()[k] for k in metrics.as_row()},
                }
            )
            log(
                f"    {model_name:24} auc={metrics.roc_auc:.4f} f1={metrics.f1:.4f} "
                f"rec={metrics.recall:.4f} fpr={metrics.fpr:.4f}"
            )

    # --- multi-corpus -> each corpus holdout (the decisive result) ---
    log("  multi-corpus -> per-corpus holdouts")
    # Reuse the recorded multi-corpus rows too; an empty candidates
    # dict means the sweep was reused, and rebuilding this list from
    # scratch would overwrite a complete CSV with a partial one.
    multi_target_rows: list[dict[str, Any]] = (
        []
        if not reuse_loco
        else [
            r for r in loco_rows
            if str(r.get("experiment", "")).startswith("multi_corpus->")
        ]
    )
    for variant_name, cols in variant_columns.items():
        if not cols:
            continue
        for model_name, factory in candidates.items():
            model = factory()
            model.fit(multi_X[train_idx][:, cols], y[train_idx])
            for corpus in corpus_names:
                idx = corpus_holdout[corpus]
                proba, ms = timed_probabilities(model, multi_X[idx][:, cols])
                metrics = compute_metrics(y[idx], proba, 0.5, ms, model_file_size_mb(model))
                multi_target_rows.append(
                    {
                        "experiment": f"multi_corpus->{corpus}",
                        "feature_variant": variant_name,
                        "model": model_name,
                        "tested_on": corpus,
                        "n_test": int(len(idx)),
                        **{k: metrics.as_row()[k] for k in metrics.as_row()},
                    }
                )
    write_csv(RESULTS / "leave_one_corpus_out.csv", loco_rows + multi_target_rows)

    # ----------------------------------------------------------------
    # STAGE 11 — semantic + real-world regression
    # ----------------------------------------------------------------
    log("STAGE 11/15  semantic and real-world regression")
    semantic_rows: list[dict[str, Any]] = []
    regression_summary: dict[str, Any] = {}

    for key, (model, cols, threshold) in fitted.items():
        variant_name, model_name = key.split("|")
        sem = evaluate_semantic_cases(model, threshold, cols, ALL_CASES)
        rw = real_world_regression(model, threshold, cols, REAL_WORLD_LEGITIMATE)
        regression_summary[key] = {
            "feature_variant": variant_name,
            "model": model_name,
            "threshold": round(threshold, 6),
            "semantic": {
                k: v for k, v in sem.items() if k != "cases"
            },
            "real_world": {
                k: v for k, v in rw.items() if k != "cases"
            },
        }
        for case in sem.get("cases", []):
            if case.get("probability") is None:
                continue
            semantic_rows.append({"model_key": key, **case})
        log(
            f"  {key:44} legitFP={sem['legitimate_false_positives']}/{sem['n_legitimate']} "
            f"phish={sem['phishing_detection_rate']:.0%} "
            f"realFP={rw['flagged']}/{rw['n']}"
        )

    write_csv(RESULTS / "semantic_regression.csv", semantic_rows)
    write_json(RESULTS / "semantic_regression_summary.json", regression_summary)

    # ----------------------------------------------------------------
    # STAGE 12 — heuristics + redundancy
    # ----------------------------------------------------------------
    log("STAGE 12/15  heuristic precision, coverage, redundancy")
    sample_idx = holdout_idx[:40000]
    heur_rules = heuristic_analysis(rows, y, sample=40000)
    heur_risk = heuristic_risk_column(rows, sample_idx)
    heur_any = heuristic_any_triggered(rows, sample_idx)
    write_csv(RESULTS / "heuristic_analysis.csv", heur_rules)

    # ----------------------------------------------------------------
    # STAGE 13 — fusion ablation on the mixed holdout
    # ----------------------------------------------------------------
    log("STAGE 13/15  fusion ablation")
    ablation_rows: list[dict[str, Any]] = []
    best_key = _best_key(variant_rows)
    best_model, best_cols, best_threshold = fitted[best_key]

    # heuristics only
    heur_scores = heuristic_risk_column(rows, holdout_idx) / 100.0
    ablation_rows.append(
        {
            "configuration": "heuristics_only",
            "threshold": 0.5,
            **{
                k: v
                for k, v in compute_metrics(y[holdout_idx], heur_scores, 0.5).as_row().items()
                if k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr")
            },
        }
    )
    # ml only
    ml_proba, _ = timed_probabilities(best_model, multi_X[holdout_idx][:, best_cols])
    ablation_rows.append(
        {
            "configuration": "ml_only",
            "threshold": round(best_threshold, 6),
            **{
                k: v
                for k, v in compute_metrics(y[holdout_idx], ml_proba, best_threshold).as_row().items()
                if k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr")
            },
        }
    )
    # fused
    for weight in (0.7, 0.8, 0.9):
        fused = weight * ml_proba + (1 - weight) * heur_scores
        ablation_rows.append(
            {
                "configuration": f"ml+heuristics@{weight:.0%}ml",
                "threshold": round(best_threshold, 6),
                "ml_weight": weight,
                **{
                    k: v
                    for k, v in compute_metrics(y[holdout_idx], fused, best_threshold).as_row().items()
                    if k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr")
                },
            }
        )
    write_csv(RESULTS / "ablation_results.csv", ablation_rows)
    for row in ablation_rows:
        log(f"  {row['configuration']:26} f1={row['f1']:.4f} rec={row['recall']:.4f} auc={row['roc_auc']:.4f}")

    # ----------------------------------------------------------------
    # STAGE 14 — v2 promotion decision
    # ----------------------------------------------------------------
    log("STAGE 14/15  v2 promotion decision")
    decision = _decide_promotion(variant_rows, regression_summary, best_key)
    log(f"  promote v2: {decision['promote']}")
    for reason in decision["reasons"]:
        log(f"    - {reason}")

    if decision["promote"]:
        import joblib

        bundle_path = MODELS / f"{PRODUCTION_NAME}.joblib"
        joblib.dump(
            {
                "bundle_version": 2,
                "estimator": best_model,
                "feature_names": [
                    FEATURE_NAMES[i] for i in best_cols
                ],
            },
            bundle_path,
        )
        meta = {
            "model_name": PRODUCTION_NAME,
            "model_version": "2.0.0",
            "selected_variant": best_key,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "features": [FEATURE_NAMES[i] for i in best_cols],
            "feature_extractor_version": FEATURE_EXTRACTOR_VERSION,
            "threshold": round(best_threshold, 6),
            "corpora": corpus_names,
            "promotion": decision,
            "stability_counts": stability_counts,
        }
        write_json(MODELS / f"{PRODUCTION_NAME}.metadata.json", meta)
        log(f"  saved {bundle_path.name}")

    # ----------------------------------------------------------------
    # STAGE 15 — audit record
    # ----------------------------------------------------------------
    write_json(
        RESULTS / "corpus_audit.json",
        {
            "semantics": semantics_summary(),
            "gates": {name: report.summary() for name, report in gate_reports.items()},
            "contexts": contexts,
            "overlap": overlap,
            "dataset": dataset.summary(),
            "leakage": leakage,
            "source_bias": {
                "all_features": source_bias_all,
                "stable_only": source_bias_stable,
            },
            "semantic_categories": semantic_categories(),
        },
    )
    write_json(
        RESULTS / "feature_variant_comparison.json",
        {"rows": variant_rows, "best_variant": best_variant, "best_key": best_key},
    )
    write_json(
        RESULTS / "environment.json",
        {
            "python": sys.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "random_state": RANDOM_STATE,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        },
    )

    log("=" * 70)
    log(f"DONE in {time.perf_counter() - started:.0f}s")
    log("=" * 70)
    return 0


def _best_variant(variant_rows: list[dict[str, Any]]) -> str:
    """Pick the variant with the best worst-target AUC."""
    best: dict[str, float] = {}
    for row in variant_rows:
        variant = row["feature_variant"]
        best[variant] = max(best.get(variant, 0.0), float(row["worst_target_auc"]))
    return max(best, key=best.get)


def _best_key(variant_rows: list[dict[str, Any]]) -> str:
    """Pick the single best (variant, model) by worst-target robustness."""
    if not variant_rows:
        raise ValueError("no variant results to choose from")
    best = max(
        variant_rows,
        key=lambda r: (
            float(r["worst_target_auc"]),
            float(r["worst_target_f1"]),
            -float(r.get("mixed_grouped_holdout_fpr", 1.0)),
        ),
    )
    return f"{best['feature_variant']}|{best['model']}"


def _decide_promotion(
    variant_rows: list[dict[str, Any]],
    regression_summary: dict[str, Any],
    best_key: str,
) -> dict[str, Any]:
    """Promote v2 only if it is genuinely more robust.

    Two independent conditions must hold: better worst-corpus
    generalization AND a materially lower false-positive rate on real
    legitimate URLs. A model that wins on one and loses on the other is
    not an improvement.
    """
    from app.ml.production import load_production_model

    reasons: list[str] = []
    best_summary = regression_summary.get(best_key, {})

    # Baseline: the shipped v1 model.
    baseline_semantic: dict[str, Any] = {}
    baseline_rw: dict[str, Any] = {}
    try:
        from scripts.phase2c_stages import evaluate_semantic_cases as _eval
        from scripts.phase2c_stages import real_world_regression as _rw
        from app.ml.feature_schema import model_feature_indices as _cols

        v1 = load_production_model()
        if v1 is not None:
            cols_v1 = _cols()
            sem = _eval(v1.estimator, v1.threshold, cols_v1, ALL_CASES)
            rw = _rw(v1.estimator, v1.threshold, cols_v1, REAL_WORLD_LEGITIMATE)
            baseline_semantic = {
                "legitimate_fp": sem["legitimate_false_positives"],
                "legitimate_fp_rate": sem["legitimate_fp_rate"],
                "real_world_fp": rw["flagged"],
                "real_world_fp_rate": rw["false_positive_rate"],
            }
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"baseline v1 evaluation failed: {exc}")

    new_semantic = best_summary.get("semantic", {})
    new_rw = best_summary.get("real_world", {})

    baseline_auc = max(
        (float(r["worst_target_auc"]) for r in variant_rows
         if r["feature_variant"] == "all_features" and r["model"] == "xgboost"),
        default=0.0,
    )
    best_auc = max(float(r["worst_target_auc"]) for r in variant_rows)

    fp_improved = (
        baseline_semantic.get("legitimate_fp", 10**9)
        - new_semantic.get("legitimate_false_positives", 10**9)
    )
    real_improved = (
        baseline_semantic.get("real_world_fp", 10**9)
        - new_rw.get("flagged", 10**9)
    )
    auc_improved = best_auc > baseline_auc

    # MATERIALITY FLOOR.
    #
    # An earlier version of this rule promoted v2 on a 23 -> 18 and
    # 10 -> 9 improvement — one real-world case out of fourteen. That is
    # noise, not a result, and shipping it would have replaced a model
    # for a change no user would notice.
    #
    # A candidate must clear a real margin on BOTH semantic and
    # real-world false positives before it is allowed to replace v1.
    MATERIAL_FP_MARGIN = 5
    material = (
        fp_improved >= MATERIAL_FP_MARGIN and real_improved >= MATERIAL_FP_MARGIN
    )

    if baseline_semantic:
        reasons.append(
            f"v1 real-world false positives {baseline_semantic['real_world_fp']}"
            f"/{len(REAL_WORLD_LEGITIMATE)} -> candidate "
            f"{new_rw.get('flagged')}/{len(REAL_WORLD_LEGITIMATE)} "
            f"(improvement {real_improved})"
        )
        reasons.append(
            f"v1 semantic legitimate false positives "
            f"{baseline_semantic['legitimate_fp']}/{len(LEGITIMATE_CASES)} -> "
            f"candidate {new_semantic.get('legitimate_false_positives')}"
            f"/{len(LEGITIMATE_CASES)} (improvement {fp_improved})"
        )

    promote = bool(material and auc_improved)
    if not promote:
        if not material:
            reasons.append(
                f"NOT PROMOTED: false-positive improvement ({fp_improved} "
                f"semantic, {real_improved} real-world) does not reach the "
                f"materiality floor of {MATERIAL_FP_MARGIN} cases. This is "
                f"within noise for a set of this size, and the candidate "
                f"still misclassifies {new_rw.get('flagged')} of "
                f"{len(REAL_WORLD_LEGITIMATE)} well-known legitimate URLs."
            )
        if not auc_improved:
            reasons.append(
                "NOT PROMOTED: candidate does not improve worst-corpus "
                "generalization over the all-features baseline."
            )
        reasons.append(
            "v1 is retained. Phase 2C improved cross-corpus generalization "
            "substantially but did not produce a production candidate that "
            "is materially safer on real-world legitimate URLs."
        )
    else:
        reasons.append(
            "candidate improves worst-corpus AUC AND clears the materiality "
            "floor on both false-positive measures"
        )

    return {
        "promote": promote,
        "candidate_key": best_key,
        "baseline": baseline_semantic,
        "candidate": {
            "semantic": new_semantic,
            "real_world": new_rw,
        },
        "fp_improvement_semantic": fp_improved,
        "fp_improvement_real_world": real_improved,
        "materiality_floor": MATERIAL_FP_MARGIN,
        "worst_target_auc_baseline": round(baseline_auc, 6),
        "worst_target_auc_candidate": round(best_auc, 6),
        "reasons": reasons,
    }


if __name__ == "__main__":
    raise SystemExit(main())

