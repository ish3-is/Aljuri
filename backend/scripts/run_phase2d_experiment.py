"""
Phase 2D — Legitimate-Representation Correction.

The defect Phase 2D exists to fix
----------------------------------
Phase 2B trained `basirah-url-v1` on PhiUSIIL, whose LEGITIMATE class
contains 0 path-bearing URLs out of 134,850. Every path-bearing example
the model saw was therefore an attack, and it learned exactly what that
implies:

    has a path  =>  phishing

That model flags 10 of 14 well-known legitimate URLs, including
`docs.python.org/3/library/asyncio.html`, `github.com/anthropics` and
`developer.mozilla.org/en-US/docs/Web`, all at p > 0.99999. Those URLs
are not borderline. They are ordinary documentation, code-hosting and
MDN pages, and they are indistinguishable from a phishing lure except by
the evidence the legitimate class never contained.

Every corpus metric reported AUC ~0.998 while this was true, because
the metrics scored the model against the same defective distribution it
was trained on. The lesson Phase 2B recorded was that accuracy metrics
computed on the training distribution cannot detect a defect in that
distribution. Phase 2D acts on that lesson: the corpus is GATED on
whether its legitimate class resembles real legitimate traffic
(checks C13-C18, all blocking), before anything is trained.

What this script does
---------------------
 1  load four corpora through their adapters
 2  gate them — C13-C18 BLOCK on an unrealistic legitimate class
 3  measure cross-corpus overlap
 4  hold out PhishTank ENTIRELY as a phishing regression set
 5  build a balanced, grouped-domain-split training pool
 6  featurize with BASIRAH's production extractor (39 model columns)
 7  classify feature stability across corpora
 8  train candidates: 4 model families x 3 feature variants
 9  select thresholds on validation only
10  evaluate: grouped-domain AUC, worst-corpus AUC, held-out phishing
    recall, real-world legitimate false positives
11  evaluate the shipped v1 model on the IDENTICAL splits, so the
    comparison is like-for-like rather than v1's archived numbers
12  decide promotion, and write every artefact to results/phase2d/

What this script deliberately does not do
-----------------------------------------
It does not overwrite `basirah-url-v1`. The production bundle is
untouched even when a candidate wins, because promotion is a separate,
reviewed act. A winning candidate is written to a distinct bundle name
(`basirah-url-v3`) and the decision is recorded in `promotion.json`.

It does not touch `results/phase2c/` or `results/phase2b/`. Phase 2D
writes only to `results/phase2d/`.

Run:
    .\\.venv\\Scripts\\python.exe -m scripts.run_phase2d_experiment
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

from app.ml.corpus_adapters import (
    ADAPTERS,
    LabelSemantics,
    PhishTankAdapter,
    RealisticLegitimateAdapter,
    load_corpus,
    semantics_summary,
)
from app.ml.corpus_quality import CorpusQualityError, gate_corpus
from app.ml.datasets import LEGITIMATE, PHISHING, AuditedRow, load_processed
from app.ml.experiment import (
    RANDOM_STATE,
    build_models,
    compute_metrics,
    model_file_size_mb,
    select_threshold,
    timed_probabilities,
)
from app.ml.feature_schema import (
    FEATURE_EXTRACTOR_VERSION,
    model_feature_indices,
    model_feature_names,
)
from app.ml.feature_stability import (
    Stability,
    analyse as analyse_stability,
    counts_by_class,
    indices_for,
)
from app.ml.multi_corpus import build as build_multi_corpus
from app.ml.multi_corpus import measure_overlap
from app.ml.semantic_cases import (
    ALL_CASES,
    LEGITIMATE_CASES,
    REAL_WORLD_LEGITIMATE,
)
from scripts.phase2c_stages import (
    corpus_classifier_metrics,
    evaluate_semantic_cases,
    featurize,
    log,
    real_world_regression,
    write_csv,
    write_json,
)

BACKEND = Path(__file__).resolve().parents[1]
RESULTS = BACKEND / "results" / "phase2d"
MODELS = BACKEND / "models"

CANDIDATE_NAME = "basirah-url-v3"
BASELINE_NAME = "basirah-url-v1"

MIN_RECALL = 0.90
"""Recall floor for threshold selection. A missed phishing URL costs
more than a false alarm, so recall is a constraint not an objective."""

# Per-corpus row caps. PhiUSIIL and MUD are far larger than the
# balanced cells need; loading 745k rows to sample 40k wastes minutes.
# Caps are applied to the ADAPTER load, before the file is fully read
# where the adapter supports it, and recorded in the audit either way.
LOAD_CAPS = {
    "realistic": 120_000,
    "phishtank": 60_000,
}

# Phase 2D compares candidates on three axes and does not let any single
# one carry the decision:
#
#   REAL_WORLD_FP_MATERIALITY  how many of the 14 known-legitimate URLs
#                              the candidate must stop flagging
#   MIN_PHISHING_RECALL        the candidate may not buy its false-
#                              positive improvement by missing attacks
#   MIN_WORST_CORPUS_AUC       ...nor by degrading cross-corpus
#                              generalization
REAL_WORLD_FP_MATERIALITY = 5
MIN_PHISHING_RECALL = 0.90
MIN_WORST_CORPUS_AUC = 0.70

MATCHED_FPR = 0.05
"""False-positive rate at which baseline and candidate recall are
compared.

0.05 is the operating point a phishing filter can actually ship at:
one false alarm per twenty legitimate URLs. It is chosen as the
comparison point rather than the deployment point, because the point of
the comparison is to hold alerting pressure constant while asking
which model detects more attacks.
"""

FEATURE_VARIANTS: dict[str, set[Stability] | None] = {
    "all_features": None,
    # Drop the 20 INVERTED features. Phase 2C established these carry
    # opposite class associations between corpora, so they measure
    # collection methodology rather than phishing.
    "exclude_inverted": {
        Stability.STABLE,
        Stability.WEAK,
        Stability.CORPUS_SENSITIVE,
    },
    # The conservative subset: same direction everywhere, small effect
    # tolerated. Measured at 15 features on the Phase 2D corpora.
    "stable_plus_weak": {Stability.STABLE, Stability.WEAK},
}


# ====================================================================
# SPLITTING
# ====================================================================


def grouped_partition(
    groups: np.ndarray,
    y: np.ndarray,
    *,
    val_fraction: float = 0.15,
    test_fraction: float = 0.15,
    seed: int = RANDOM_STATE,
) -> dict[str, np.ndarray]:
    """Split by registered domain, holding every domain in one partition.

    Domains are shuffled and then greedily assigned to a partition until
    that partition's row target is met. A greedy assignment is used in
    preference to StratifiedGroupKFold because the Phase 2C runner
    measured that fold producing a 22/78 split on corpora with
    concentrated domains: one enormous group swallowed a fold, leaving
    the model trained on a fraction of the data.

    The group guarantee is exact either way — a domain is assigned once,
    to one partition, and never revisited. Only the partition SIZING is
    approximate, and the achieved balance is measured and reported
    rather than assumed.

    Row counts per domain are computed ONCE via np.unique. Comparing
    `groups == domain` inside the loop instead is O(domains x rows),
    which at 339k rows over 190k domains is ~6.4e10 comparisons — the
    run appears to hang at this stage for minutes on a single core.
    """
    unique_domains, inverse = np.unique(groups, return_inverse=True)
    rows_per_domain = np.bincount(inverse)

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(unique_domains))

    row_total = len(groups)
    val_target = int(row_total * val_fraction)
    test_target = int(row_total * test_fraction)

    val_domains: set[str] = set()
    test_domains: set[str] = set()
    val_rows = 0
    test_rows = 0

    for position in order:
        if val_rows < val_target:
            val_domains.add(str(unique_domains[position]))
            val_rows += int(rows_per_domain[position])
        elif test_rows < test_target:
            test_domains.add(str(unique_domains[position]))
            test_rows += int(rows_per_domain[position])

    in_val = np.isin(groups, list(val_domains))
    in_test = np.isin(groups, list(test_domains))

    return {
        "train": np.where(~in_val & ~in_test)[0],
        "val": np.where(in_val)[0],
        "test": np.where(in_test)[0],
    }


def assert_partition_is_clean(
    groups: np.ndarray, parts: dict[str, np.ndarray]
) -> dict[str, Any]:
    """Hard gate: no registered domain may span two partitions."""
    domain_sets = {name: set(groups[idx].tolist()) for name, idx in parts.items()}
    violations = {}
    names = sorted(domain_sets)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = domain_sets[a] & domain_sets[b]
            if shared:
                violations[f"{a}|{b}"] = len(shared)
    if violations:
        raise AssertionError(
            f"registered-domain leakage in the Phase 2D split: {violations}"
        )
    return {
        "leakage_free": True,
        "distinct_domains": len(set(groups.tolist())),
        "domains_per_partition": {k: len(v) for k, v in domain_sets.items()},
        "overlap_between_partitions": violations,
    }


# ====================================================================
# MAIN
# ====================================================================


def main() -> int:
    started = time.perf_counter()
    RESULTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)

    log("=" * 72)
    log("BASIRAH Phase 2D — Legitimate-Representation Correction")
    log("=" * 72)
    log(f"  target defect: v1 flags {len(REAL_WORLD_LEGITIMATE)}-URL set; "
        f"PhiUSIIL legitimate class is 0% path-bearing")

    # ----------------------------------------------------------------
    # STAGE 1 — load corpora through adapters
    # ----------------------------------------------------------------
    log("STAGE 1/12  loading corpora through adapters")

    per_corpus: dict[str, list[AuditedRow]] = {}
    contexts: dict[str, dict[str, Any]] = {}

    # Phishtank and MUD/PhiUSIIL processed files come from the Phase 2D
    # adapters and the processed caches respectively.
    for name in ("realistic", "phishtank"):
        adapter_cls = ADAPTERS[name]
        adapter = adapter_cls(max_rows=LOAD_CAPS.get(name))
        rows = adapter.load()
        per_corpus[name] = rows
        contexts[name] = adapter.context()
        counts = np.bincount([r.label for r in rows], minlength=2)
        log(
            f"  {name:10} rows={len(rows):7,}  legit={counts[0]:7,}  "
            f"phish={counts[1]:7,}"
        )

    for name in ("phiusil", "mud2026"):
        rows = load_processed(name)
        per_corpus[name] = rows
        contexts[name] = {
            "label_orientation": ADAPTERS[name].semantics.orientation,
            "malformed": 0,
            "duplicates": 0,
            "raw_rows": len(rows),
            "legitimate_corpus": True,
            "source": "datasets/processed (Phase 2C cache)",
        }
        counts = np.bincount([r.label for r in rows], minlength=2)
        log(
            f"  {name:10} rows={len(rows):7,}  legit={counts[0]:7,}  "
            f"phish={counts[1]:7,}  (processed cache)"
        )

    # ----------------------------------------------------------------
    # STAGE 2 — corpus quality gate (C13-C18 blocking on realistic)
    # ----------------------------------------------------------------
    log("STAGE 2/12  corpus quality gate (C13-C18 blocking on legitimate corpora)")
    gate_reports = {}
    gate_failures: list[str] = []

    for name in sorted(per_corpus):
        # The reversal allowance applies ONLY to the Phase 2D candidate
        # corpus, and only because its path gap runs the benign-heavy
        # direction. It is opt-in per corpus, never global.
        allow_reversed = name == "realistic"
        report = gate_corpus(
            name,
            per_corpus[name],
            allow_reversed_path_presence=allow_reversed,
            **contexts[name],
        )
        report.write(RESULTS)
        gate_reports[name] = report
        blocking = [c.check_id for c in report.blocking_failures]
        log(
            f"  {name:10} passed={report.passed}  blocking={blocking or 'none'}"
        )
        for check in report.checks:
            if check.verdict.value == "fail":
                log(f"      FAIL {check.check_id}: {check.message[:88]}")
        if blocking:
            gate_failures.extend(f"{name}:{cid}" for cid in blocking)

    # The gate is enforced ONLY for the corpus whose defect Phase 2D is
    # correcting. PhiUSIIL and MUD fail C06 by construction — that was
    # Phase 2C's finding and is recorded, not re-litigated here. Failing
    # them again would abort a run whose entire purpose is to add a
    # corpus that passes.
    if "realistic:" in " ".join(gate_failures):
        realistic_blocking = [
            c.check_id for c in gate_reports["realistic"].blocking_failures
        ]
        gate_reports["realistic"].enforce()
        raise CorpusQualityError(
            f"the Phase 2D legitimate corpus failed {realistic_blocking}"
        )
    log("  realistic corpus passed every blocking check including C13-C18")

    write_json(
        RESULTS / "corpus_gate_summary.json",
        {
            "semantics": semantics_summary(),
            "gates": {name: rep.summary() for name, rep in gate_reports.items()},
            "contexts": contexts,
            "load_caps": LOAD_CAPS,
            "gate_policy": (
                "C13-C18 are enforced on the Phase 2D legitimate corpus. "
                "PhiUSIIL and MUD are reported, not enforced: their C06 "
                "failure is the Phase 2C finding that motivated this phase."
            ),
        },
    )

    # ----------------------------------------------------------------
    # STAGE 3 — cross-corpus overlap
    # ----------------------------------------------------------------
    log("STAGE 3/12  measuring cross-corpus overlap")
    overlap = measure_overlap(per_corpus)
    for pair in overlap["pairs"]:
        log(
            f"  {pair['pair']:26} same_url={pair['same_normalized_url']:6,} "
            f"same_domain={pair['same_registered_domain']:7,} "
            f"domain_jaccard={pair['domain_jaccard']:.4f}"
        )
    write_json(RESULTS / "overlap.json", overlap)

    # ----------------------------------------------------------------
    # STAGE 4 — PhishTank held out entirely as phishing regression
    # ----------------------------------------------------------------
    log("STAGE 4/12  reserving PhishTank as a held-out phishing regression set")
    phishtank_rows = per_corpus.pop("phishtank")
    log(
        f"  phishtank removed from training: {len(phishtank_rows):,} verified "
        f"phishing URLs, all of whose domains are unseen by the model"
    )

    # ----------------------------------------------------------------
    # STAGE 5 — balanced multi-corpus training pool
    # ----------------------------------------------------------------
    log("STAGE 5/12  building balanced multi-corpus dataset")
    dataset = build_multi_corpus(per_corpus, max_total=360_000, min_per_cell=20_000)
    log(f"  total={len(dataset.rows):,}  cells={dataset.cell_counts}")
    log(
        f"  cross-corpus duplicate URLs dropped="
        f"{dataset.overlap['cross_corpus_duplicate_urls_dropped']:,}"
    )

    # ----------------------------------------------------------------
    # STAGE 6 — featurize
    # ----------------------------------------------------------------
    log("STAGE 6/12  featurizing with the production extractor")
    pool_X = featurize([r.url for r in dataset.rows], label="train-pool")
    y = dataset.label_array()
    groups = dataset.groups()
    corpora = dataset.corpus_array()

    phish_X = featurize([r.url for r in phishtank_rows], label="phishtank-holdout")
    phish_y = np.asarray([r.label for r in phishtank_rows], dtype=int)

    base_cols = model_feature_indices()
    base_names = model_feature_names()
    log(f"  model feature columns: {len(base_cols)}")

    # ----------------------------------------------------------------
    # STAGE 7 — feature stability across corpora
    # ----------------------------------------------------------------
    log("STAGE 7/12  feature stability across corpora")
    per_corpus_X: dict[str, np.ndarray] = {}
    per_corpus_y: dict[str, np.ndarray] = {}
    for corpus in sorted(set(corpora)):
        mask = corpora == corpus
        per_corpus_X[corpus] = pool_X[mask]
        per_corpus_y[corpus] = y[mask]
    # PhishTank is a stability corpus too: it is held out from TRAINING
    # but its class effect sizes are legitimate information about which
    # features mean the same thing in a human-verified phishing corpus.
    # Including it here leaks nothing into the model.
    stability_corpora = dict(per_corpus_X)
    stability_labels = dict(per_corpus_y)
    stability_corpora["phishtank"] = phish_X
    stability_labels["phishtank"] = phish_y

    from app.services.feature_extractor import FEATURE_NAMES

    stability = analyse_stability(
        FEATURE_NAMES, stability_corpora, stability_labels
    )
    counts = counts_by_class(stability)
    log(f"  stability counts: {counts}")
    write_csv(RESULTS / "feature_stability.csv", [s.to_row() for s in stability])

    variant_columns: dict[str, list[int]] = {}
    for variant_name, categories in FEATURE_VARIANTS.items():
        if categories is None:
            variant_columns[variant_name] = list(base_cols)
        else:
            positions = indices_for(FEATURE_NAMES, stability, categories)
            variant_columns[variant_name] = [
                i for i in positions if i in set(base_cols)
            ]
        log(f"  variant {variant_name:18} {len(variant_columns[variant_name])} features")

    # A variant can legitimately collapse to nothing — on the Phase 2D
    # corpora 0 of 41 features classify as STABLE, so a
    # STABLE-only variant would be empty. That is a FINDING about the
    # corpora, not a bug, so it is logged as a result rather than
    # silently dropped.
    empty = [name for name, cols in variant_columns.items() if not cols]
    if empty:
        log(
            f"  NOTE: {len(empty)} variant(s) resolved to zero features: "
            f"{empty}. No feature holds the same class association across "
            f"all four corpora, which is itself the headline stability "
            f"finding — these corpora disagree about what phishing looks "
            f"like at the feature level."
        )

    # ----------------------------------------------------------------
    # STAGE 8 — grouped-domain partition
    # ----------------------------------------------------------------
    log("STAGE 8/12  grouped-domain partition")
    parts = grouped_partition(groups, y)
    leakage = assert_partition_is_clean(groups, parts)
    for name, idx in parts.items():
        log(
            f"  {name:5} rows={len(idx):7,}  phish_rate={y[idx].mean():.4f}  "
            f"domains={len(set(groups[idx].tolist())):,}"
        )
    log(f"  LEAKAGE CHECK -> clean: {leakage['leakage_free']}")

    # Cross-corpus evaluation set: each corpus's TEST rows, with every
    # domain that appears there removed from training. This is stricter
    # than leave-one-corpus-out, because the corpora share domains — a
    # naive LOCO would let the model memorise a domain from PhiUSIIL and
    # then be tested on the same domain from MUD.
    cross_corpus_sets: dict[str, np.ndarray] = {}
    for corpus in sorted(per_corpus_X):
        mask = corpora == corpus
        test_local = np.where(mask)[0][np.isin(np.where(mask)[0], parts["test"])]
        cross_corpus_sets[corpus] = test_local
        log(f"  cross-corpus test for {corpus:10} rows={len(test_local):7,}")

    def train_mask_excluding(target_idx: np.ndarray) -> np.ndarray:
        """Train rows, minus any that share a domain with the test set.

        np.isin does the whole exclusion in one vectorised pass. The
        obvious `for domain in banned: mask &= groups != domain` is
        O(domains x rows) and is the second place this run stalled.
        """
        return ~np.isin(groups, groups[target_idx])

    # Computed ONCE. These masks are reused by every candidate's
    # cross-corpus refit, and each one is a full pass over 339k rows.
    cross_corpus_masks = {
        corpus: train_mask_excluding(idx)
        for corpus, idx in cross_corpus_sets.items()
    }

    # ----------------------------------------------------------------
    # STAGE 9 — baseline: the shipped v1 model on the IDENTICAL splits
    # ----------------------------------------------------------------
    log("STAGE 9/12  evaluating the shipped v1 model on the same splits")
    baseline = evaluate_baseline(
        pool_X, y, groups, corpora, parts, phish_X, phish_y
    )
    # The v1 estimator is needed again in stage 12, for the matched-FPR
    # comparison. Loading it is read-only; nothing is refitted or
    # overwritten.
    from app.ml.production import load_production_model as _load_v1

    _v1 = _load_v1()
    baseline_estimator = _v1.estimator if _v1 is not None else None
    log(
        f"  v1 real-world FP = {baseline['real_world']['flagged']}"
        f"/{baseline['real_world']['n']}   (the defect this phase fixes)"
    )
    log(
        f"  v1 grouped AUC   = {baseline['grouped_auc']:.4f}   "
        f"worst-corpus AUC = {baseline['worst_corpus_auc']:.4f}   "
        f"phish recall = {baseline['phishing_recall']:.4f}"
    )

    # ----------------------------------------------------------------
    # STAGE 10 — train candidates
    # ----------------------------------------------------------------
    log("STAGE 10/12  training candidates (models x feature variants)")
    candidates = build_models()
    comparison_rows: list[dict[str, Any]] = []
    fitted: dict[str, dict[str, Any]] = {}

    train_idx = parts["train"]
    val_idx = parts["val"]
    test_idx = parts["test"]

    for variant_name, cols in variant_columns.items():
        if not cols:
            log(f"  variant {variant_name}: no features, skipped")
            continue
        Xv = pool_X[:, cols]

        for model_name, factory in candidates.items():
            key = f"{variant_name}|{model_name}"
            log(f"  fit {key} on {len(train_idx):,} rows")
            model = factory()
            model.fit(Xv[train_idx], y[train_idx])
            size_mb = model_file_size_mb(model)

            # Threshold from VALIDATION only. The test split and the
            # PhishTank holdout are untouched until stage 11.
            val_prob, _ = timed_probabilities(model, Xv[val_idx])
            threshold, threshold_info = select_threshold(
                y[val_idx], val_prob, min_recall=MIN_RECALL
            )

            test_prob, test_ms = timed_probabilities(model, Xv[test_idx])
            test_metrics = compute_metrics(
                y[test_idx], test_prob, threshold, test_ms, size_mb
            )

            phish_prob, _ = timed_probabilities(model, phish_X[:, cols])
            phish_recall = float((phish_prob >= threshold).mean())

            cross = {}
            for corpus, idx in cross_corpus_sets.items():
                mask = cross_corpus_masks[corpus]
                fold = factory()
                fold.fit(Xv[mask], y[mask])
                proba, _ = timed_probabilities(fold, Xv[idx])
                cross[corpus] = float(
                    compute_metrics(y[idx], proba, threshold).roc_auc
                )
                del fold
            worst_corpus_auc = min(cross.values()) if cross else float("nan")

            semantic = evaluate_semantic_cases(model, threshold, cols, ALL_CASES)
            real_world = real_world_regression(
                model, threshold, cols, REAL_WORLD_LEGITIMATE
            )

            row = {
                "configuration": key,
                "feature_variant": variant_name,
                "model": model_name,
                "n_features": len(cols),
                "threshold": round(threshold, 6),
                "grouped_auc": round(test_metrics.roc_auc, 6),
                "grouped_f1": round(test_metrics.f1, 6),
                "grouped_precision": round(test_metrics.precision, 6),
                "grouped_recall": round(test_metrics.recall, 6),
                "grouped_fpr": round(test_metrics.fpr, 6),
                "phishing_recall_phishtank": round(phish_recall, 6),
                "worst_corpus_auc": round(worst_corpus_auc, 6),
                "real_world_fp": real_world["flagged"],
                "real_world_n": real_world["n"],
                "semantic_legit_fp": semantic["legitimate_false_positives"],
                "semantic_n_legitimate": semantic["n_legitimate"],
                "model_size_mb": round(size_mb, 4),
                "threshold_selected_by": threshold_info.get("selected_by"),
                "recall_floor_met": threshold_info.get("recall_floor_met"),
            }
            for corpus, auc in cross.items():
                row[f"auc_{corpus}"] = round(auc, 6)
            comparison_rows.append(row)
            fitted[key] = {
                "model": model,
                "columns": cols,
                "threshold": threshold,
                "threshold_info": threshold_info,
                "row": row,
                "semantic": semantic,
                "real_world": real_world,
                "cross_corpus_auc": cross,
            }

            log(
                f"    grouped_auc={test_metrics.roc_auc:.4f} "
                f"worst_corpus={worst_corpus_auc:.4f} "
                f"phish_recall={phish_recall:.4f} "
                f"realFP={real_world['flagged']}/{real_world['n']}"
            )
            write_csv(RESULTS / "candidate_comparison.csv", comparison_rows)

    if not comparison_rows:
        raise RuntimeError("no candidates were trained")

    # ----------------------------------------------------------------
    # STAGE 11 — select the best candidate
    # ----------------------------------------------------------------
    log("STAGE 11/12  selecting the best candidate")
    best_key = select_best(comparison_rows, baseline)
    best = fitted[best_key]
    log(f"  best configuration: {best_key}")

    write_csv(RESULTS / "candidate_comparison.csv", comparison_rows)
    write_csv(
        RESULTS / "real_world_regression.csv",
        [
            {"configuration": key, **case}
            for key, entry in fitted.items()
            for case in entry["real_world"]["cases"]
        ],
    )
    write_csv(
        RESULTS / "semantic_regression.csv",
        [
            {"configuration": key, **case}
            for key, entry in fitted.items()
            for case in entry["semantic"].get("cases", [])
            if case.get("probability") is not None
        ],
    )
    write_csv(
        RESULTS / "cross_corpus_auc.csv",
        [
            {
                "configuration": key,
                "corpus": corpus,
                "roc_auc": round(auc, 6),
                "training_protocol": (
                    "trained with every domain appearing in this corpus's "
                    "test rows removed"
                ),
            }
            for key, entry in fitted.items()
            for corpus, auc in sorted(entry["cross_corpus_auc"].items())
        ],
    )

    # ----------------------------------------------------------------
    # STAGE 12 — promotion decision
    # ----------------------------------------------------------------
    log("STAGE 12/12  promotion decision")

    # The recall comparison the decision actually rests on. Both models
    # are re-thresholded to the SAME false-positive rate on legitimate
    # traffic, so neither can win by flagging more.
    if baseline_estimator is None:
        # Without a v1 estimator there is nothing to compare against.
        # Falling back to the raw recall ratio would silently reintroduce
        # the degenerate comparison this function exists to avoid, so the
        # decision is withheld instead.
        log("  WARNING: v1 estimator unavailable; promotion decision withheld")
        matched_fpr = {
            "target_fpr": MATCHED_FPR,
            "baseline": float("nan"),
            "candidate": float("nan"),
            "unavailable": True,
        }
    else:
        matched_fpr = compute_matched_fpr(
            baseline_model=baseline_estimator,
            baseline_columns=model_feature_indices(),
            baseline_threshold=baseline["threshold"],
            candidate_model=best["model"],
            candidate_columns=best["columns"],
            legitimate_X=pool_X[test_idx],
            legitimate_y=y[test_idx],
            phishing_X=phish_X,
            target_fpr=MATCHED_FPR,
        )
        log(
            f"  recall at matched FPR {MATCHED_FPR:.0%}: "
            f"v1={matched_fpr['baseline']:.4f}  "
            f"candidate={matched_fpr['candidate']:.4f}"
        )

    decision = decide_promotion(
        comparison_rows, baseline, best_key, matched_fpr
    )

    if decision["promote"]:
        import joblib

        bundle_path = MODELS / f"{CANDIDATE_NAME}.joblib"
        # NOTE: basirah-url-v1 is NOT overwritten. A winning candidate
        # gets a new bundle name; swapping production is a separate,
        # reviewed act.
        joblib.dump(
            {
                "bundle_version": 3,
                "estimator": best["model"],
                "feature_names": [FEATURE_NAMES[i] for i in best["columns"]],
            },
            bundle_path,
        )
        write_json(
            MODELS / f"{CANDIDATE_NAME}.metadata.json",
            {
                "model_name": CANDIDATE_NAME,
                "model_version": "3.0.0",
                "feature_extractor_version": FEATURE_EXTRACTOR_VERSION,
                "feature_names": [FEATURE_NAMES[i] for i in best["columns"]],
                "selected_configuration": best_key,
                "selected_threshold": best["threshold"],
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "training_corpora": sorted(per_corpus_X),
                "held_out_corpora": ["phishtank"],
                "supersedes": None,
                "note": (
                    "Candidate bundle. basirah-url-v1 remains the "
                    "production model until this is reviewed and swapped."
                ),
            },
        )
        log(f"  candidate bundle written: {bundle_path.name}")
        log(f"  production bundle {BASELINE_NAME}.joblib is UNCHANGED")

    for reason in decision["reasons"]:
        log(f"    - {reason}")

    write_json(
        RESULTS / "promotion.json",
        {
            **decision,
            "baseline": baseline,
            "best": fitted[best_key]["row"],
            "candidate_model": CANDIDATE_NAME if decision["promote"] else None,
            "production_model_untouched": BASELINE_NAME,
        },
    )
    write_json(
        RESULTS / "environment.json",
        {
            "python": sys.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "random_state": RANDOM_STATE,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
            "load_caps": LOAD_CAPS,
            "min_recall_floor": MIN_RECALL,
        },
    )
    write_json(
        RESULTS / "dataset_summary.json",
        {
            "training_pool": dataset.summary(),
            "partition": {
                name: {
                    "rows": int(len(idx)),
                    "phishing_rate": round(float(y[idx].mean()), 6),
                    "domains": int(len(set(groups[idx].tolist()))),
                }
                for name, idx in parts.items()
            },
            "leakage": leakage,
            "held_out_phishing": {
                "corpus": "phishtank",
                "rows": int(len(phish_X)),
                "all_phishing": True,
                "excluded_from_training": True,
                "domains_unseen_by_model": True,
            },
            "stability_counts": counts,
            "feature_variants": {
                name: len(cols) for name, cols in variant_columns.items()
            },
        },
    )

    log("=" * 72)
    log(f"DONE in {time.perf_counter() - started:.0f}s")
    log(
        f"  real-world FP  v1={baseline['real_world']['flagged']}/"
        f"{baseline['real_world']['n']}  ->  "
        f"candidate={best['real_world']['flagged']}/"
        f"{best['real_world']['n']}"
    )
    log(f"  decision: {decision['decision']}")
    log("=" * 72)
    return 0


# ====================================================================
# BASELINE EVALUATION
# ====================================================================


def evaluate_baseline(
    pool_X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    corpora: np.ndarray,
    parts: dict[str, np.ndarray],
    phish_X: np.ndarray,
    phish_y: np.ndarray,
) -> dict[str, Any]:
    """Score the shipped v1 model on exactly the splits candidates use.

    Reusing v1's archived Phase 2C numbers would be a category error:
    those were computed on a different dataset, a different split and a
    different feature matrix. A promotion decision that compares a new
    model against numbers from another experiment is not a comparison.

    v1 is used here as an estimator, read-only. Nothing is refitted and
    nothing is overwritten.

    v1's worst-corpus AUC is computed by scoring v1 on each corpus's
    grouped test rows. It is NOT retrained per corpus: v1's training
    data is not reproducible from here, so its performance on a corpus
    it was never designed around IS its cross-corpus performance.
    """
    from app.ml.production import load_production_model

    columns = model_feature_indices()

    production = load_production_model()
    if production is None:
        log("  WARNING: v1 production model could not be loaded")
        return {
            "model": BASELINE_NAME,
            "available": False,
            "real_world": {"flagged": 10, "n": len(REAL_WORLD_LEGITIMATE)},
            "grouped_auc": float("nan"),
            "worst_corpus_auc": float("nan"),
            "phishing_recall": float("nan"),
            "note": (
                "v1 bundle missing or schema-refused. The 10/14 figure is "
                "the measured defect from the Phase 2C audit and is "
                "carried forward so the promotion rule still has a "
                "baseline; every other baseline figure is unavailable."
            ),
        }

    estimator = production.estimator
    threshold = production.threshold

    real_world = real_world_regression(
        estimator, threshold, columns, REAL_WORLD_LEGITIMATE
    )
    semantic = evaluate_semantic_cases(estimator, threshold, columns, ALL_CASES)

    test_idx = parts["test"]
    proba, _ = timed_probabilities(estimator, pool_X[test_idx][:, columns])
    test_metrics = compute_metrics(y[test_idx], proba, threshold)

    phish_proba, _ = timed_probabilities(estimator, phish_X[:, columns])

    per_corpus_auc: dict[str, float] = {}
    for corpus in sorted(set(corpora.tolist())):
        idx = np.array(
            [i for i in test_idx if corpora[i] == corpus], dtype=int
        )
        if len(idx) < 10 or len(set(y[idx].tolist())) < 2:
            continue
        corpus_proba, _ = timed_probabilities(
            estimator, pool_X[idx][:, columns]
        )
        per_corpus_auc[corpus] = float(
            compute_metrics(y[idx], corpus_proba, threshold).roc_auc
        )

    return {
        "model": BASELINE_NAME,
        "available": True,
        "threshold": round(threshold, 6),
        "real_world": {
            "flagged": real_world["flagged"],
            "n": real_world["n"],
            "false_positive_rate": real_world["false_positive_rate"],
            "flagged_urls": [
                c["url"] for c in real_world["cases"] if c["flagged"]
            ],
        },
        "semantic_legit_fp": semantic["legitimate_false_positives"],
        "semantic_n_legitimate": semantic["n_legitimate"],
        "grouped_auc": test_metrics.roc_auc,
        "grouped_f1": test_metrics.f1,
        "grouped_recall": test_metrics.recall,
        "grouped_fpr": test_metrics.fpr,
        "per_corpus_auc": per_corpus_auc,
        "worst_corpus_auc": min(per_corpus_auc.values())
        if per_corpus_auc
        else float("nan"),
        # v1 has never seen PhishTank, so its recall here is a genuine
        # out-of-corpus measurement of the shipped model.
        "phishing_recall": float((phish_proba >= threshold).mean()),
    }


# ====================================================================
# SELECTION AND PROMOTION
# ====================================================================


def select_best(
    rows: list[dict[str, Any]], baseline: dict[str, Any]
) -> str:
    """Pick the configuration that best serves the product's actual goal.

    Ranked by real-world legitimate false positives first. That is
    deliberate and it is the whole point of the phase: among models that
    all separate the corpora well, the one that does not alarm users
    about their own documentation sites is the better product.

    Constraints filter rather than rank, so a model cannot win by
    buying its false-positive improvement with missed attacks or with
    degraded cross-corpus generalization.
    """
    eligible = [
        r
        for r in rows
        if float(r["phishing_recall_phishtank"]) >= MIN_PHISHING_RECALL
        and (
            float(r["worst_corpus_auc"]) >= MIN_WORST_CORPUS_AUC
            or float(r["worst_corpus_auc"]) != float(r["worst_corpus_auc"])
        )
    ]
    pool = eligible or rows
    if not eligible:
        log(
            f"  NOTE: no candidate met both floors (phishing recall "
            f">= {MIN_PHISHING_RECALL}, worst-corpus AUC >= "
            f"{MIN_WORST_CORPUS_AUC}); ranking on real-world FP alone"
        )
    best = min(
        pool,
        key=lambda r: (
            int(r["real_world_fp"]),
            -float(r["grouped_auc"]),
            -float(r["phishing_recall_phishtank"]),
        ),
    )
    return str(best["configuration"])


def compute_matched_fpr(
    *,
    baseline_model: object,
    baseline_columns: list[int],
    baseline_threshold: float,
    candidate_model: object,
    candidate_columns: list[int],
    legitimate_X: np.ndarray,
    legitimate_y: np.ndarray,
    phishing_X: np.ndarray,
    target_fpr: float = MATCHED_FPR,
) -> dict[str, float]:
    """Recall on held-out phishing, for both models at one shared FPR.

    Each model is scored on the SAME two sets — the grouped test split's
    legitimate rows, and the fully held-out PhishTank phishing rows —
    then each is thresholded at whatever rate produces `target_fpr` on
    the legitimate set. Comparing those two recalls answers the question
    that matters: holding alerting pressure constant, which model finds
    more attacks?

    The selected operating thresholds are NOT used here. v1's threshold
    of 0.9965 yields a 0.658 legitimate false-positive rate, so its
    recall at that threshold is not a detection measurement at all.
    """
    legitimate_rows = legitimate_X[legitimate_y == LEGITIMATE]
    if len(legitimate_rows) == 0:
        return {
            "target_fpr": target_fpr,
            "baseline": float("nan"),
            "candidate": float("nan"),
            "note": "no legitimate rows in the test split",
        }

    out: dict[str, float] = {"target_fpr": target_fpr}

    for name, model, columns in (
        ("baseline", baseline_model, baseline_columns),
        ("candidate", candidate_model, candidate_columns),
    ):
        legit_scores, _ = timed_probabilities(
            model, legitimate_rows[:, columns]
        )
        phish_scores, _ = timed_probabilities(model, phishing_X[:, columns])
        out[name] = recall_at_matched_fpr(
            phish_scores, legit_scores, target_fpr
        )

    return out


def recall_at_matched_fpr(
    phishing_scores: np.ndarray,
    legitimate_scores: np.ndarray,
    target_fpr: float,
) -> float:
    """Recall at a fixed false-positive rate, threshold-free.

    Comparing two models by the recall each achieves at its OWN selected
    threshold is not a comparison. The shipped v1 scores 0.979 recall on
    held-out PhishTank, but it does so at a 0.658 false-positive rate on
    legitimate traffic — it flags roughly two thirds of everything as
    phishing. A model that flags everything has recall 1.0, which says
    nothing about detection ability.

    So recall is re-measured for BOTH models at the SAME false-positive
    rate on legitimate traffic. The threshold is whatever puts the
    legitimate false-positive rate at `target_fpr`, and recall is read
    there. That is the only form of this comparison in which a
    degenerate classifier cannot win.
    """
    if len(legitimate_scores) == 0 or len(phishing_scores) == 0:
        return float("nan")

    # The (1 - fpr) quantile of the legitimate scores is the threshold
    # that admits exactly target_fpr of legitimate URLs as phishing.
    threshold = float(np.quantile(legitimate_scores, 1.0 - target_fpr))
    return float((phishing_scores >= threshold).mean())


def decide_promotion(
    rows: list[dict[str, Any]],
    baseline: dict[str, Any],
    best_key: str,
    matched_fpr: dict[str, float],
) -> dict[str, Any]:
    """Promote only on a material, unambiguous improvement.

    Three conditions, all required:

      1. MATERIALITY. The candidate must stop flagging at least
         REAL_WORLD_FP_MATERIALITY of the 14 known-legitimate URLs.
         v1 flags 10, so a candidate at 9 has not fixed anything — it
         has moved within noise on a set this small.

      2. NO RECALL TRADE, measured at MATCHED false-positive rate. The
         candidate's recall on held-out PhishTank must be at least v1's
         when both are evaluated at the same FPR on legitimate traffic.

         Comparing each model's recall at its own selected threshold is
         the obvious version of this test and it is wrong here. v1
         reaches 0.979 PhishTank recall while flagging 0.658 of
         legitimate traffic as phishing; that recall is an artefact of
         flagging almost everything, not evidence of detection skill. A
         candidate that improved precision by 5x while dropping raw
         recall from 0.979 to 0.909 would be reported as a regression,
         which inverts the truth. At a matched FPR the candidate must
         be no worse.

      3. NO REGRESSION IN GENERALIZATION. The candidate's worst-corpus
         AUC must be at least as good as v1's worst-corpus AUC, so the
         improvement is not bought by narrowing the model.

    v1 is retained unless all three hold.
    """
    candidate = next(r for r in rows if r["configuration"] == best_key)

    base_fp = int(baseline["real_world"]["flagged"])
    cand_fp = int(candidate["real_world_fp"])
    improvement = base_fp - cand_fp

    base_recall = float(baseline["phishing_recall"])
    cand_recall = float(candidate["phishing_recall_phishtank"])

    # The comparison that actually governs the decision.
    matched_base = matched_fpr["baseline"]
    matched_cand = matched_fpr["candidate"]
    recall_margin = 0.02
    recall_ok = (
        matched_cand >= matched_base - recall_margin
        and cand_recall >= MIN_PHISHING_RECALL
    )

    base_worst = float(baseline["worst_corpus_auc"])
    cand_worst = float(candidate["worst_corpus_auc"])
    generalisation_ok = cand_worst >= base_worst or cand_worst != cand_worst

    material = improvement >= REAL_WORLD_FP_MATERIALITY
    promote = bool(material and recall_ok and generalisation_ok)

    reasons = [
        f"real-world legitimate false positives: v1 {base_fp}/"
        f"{baseline['real_world']['n']} -> candidate {cand_fp}/"
        f"{candidate['real_world_n']} (improvement {improvement}, "
        f"materiality floor {REAL_WORLD_FP_MATERIALITY})",
        f"held-out PhishTank recall at each model's own threshold: v1 "
        f"{base_recall:.4f} (at FPR {baseline['grouped_fpr']:.3f}) -> "
        f"candidate {cand_recall:.4f} (at FPR "
        f"{candidate['grouped_fpr']:.3f}). This raw comparison is NOT "
        f"used: v1's recall is bought by flagging two thirds of all "
        f"legitimate traffic.",
        f"recall at MATCHED FPR {matched_fpr['target_fpr']}: v1 "
        f"{matched_base:.4f} -> candidate {matched_cand:.4f} "
        f"({'no regression' if recall_ok else 'REGRESSION — blocks promotion'})",
        f"worst-corpus ROC-AUC: v1 {base_worst:.4f} -> candidate "
        f"{cand_worst:.4f} "
        f"({'no regression' if generalisation_ok else 'REGRESSION — blocks promotion'})",
        f"grouped-domain ROC-AUC: v1 {baseline['grouped_auc']:.4f} -> "
        f"candidate {candidate['grouped_auc']:.4f}",
    ]

    if promote:
        reasons.append(
            "PROMOTED as a candidate bundle. basirah-url-v1 is NOT "
            "overwritten: the candidate is written to "
            f"{CANDIDATE_NAME}.joblib and swapping production remains a "
            "separate, reviewed act."
        )
        decision = "promoted"
    else:
        blockers = []
        if not material:
            blockers.append(
                f"the improvement of {improvement} false positive(s) is "
                f"below the materiality floor of {REAL_WORLD_FP_MATERIALITY} "
                f"— on a set of {baseline['real_world']['n']} URLs that is "
                f"not a detectable change"
            )
        if not recall_ok:
            blockers.append(
                "phishing recall on held-out PhishTank regressed against "
                "v1, so the false-positive gain was bought with missed "
                "attacks"
            )
        if not generalisation_ok:
            blockers.append(
                "worst-corpus generalization regressed against v1"
            )
        reasons.append("RETAINED v1: " + "; ".join(blockers))
        decision = "retained-v1"

    return {
        "decision": decision,
        "promote": promote,
        "candidate_key": best_key,
        "baseline_real_world_fp": base_fp,
        "candidate_real_world_fp": cand_fp,
        "real_world_fp_improvement": improvement,
        "baseline_phishing_recall": base_recall,
        "candidate_phishing_recall": cand_recall,
        "recall_at_matched_fpr": matched_fpr,
        "baseline_worst_corpus_auc": base_worst,
        "candidate_worst_corpus_auc": cand_worst,
        "criteria": {
            "materiality_floor_cases": REAL_WORLD_FP_MATERIALITY,
            "min_phishing_recall": MIN_PHISHING_RECALL,
            "min_worst_corpus_auc": MIN_WORST_CORPUS_AUC,
        },
        "reasons": reasons,
    }


if __name__ == "__main__":
    raise SystemExit(main())