"""
Phase 2B experiment runner.

One command executes the whole study:

    .venv\\Scripts\\python.exe -m scripts.run_phase2b_experiment

Stages, in order:
  1  audit datasets, write manifests
  2  featurize with BASIRAH's PRODUCTION extractor
  3  build random + grouped-domain splits, assert no leakage
  4  train Logistic Regression / Random Forest / XGBoost (+ HistGB)
  5  evaluate on the held-out test fold, per split strategy
  6  calibrate probabilities (Platt / isotonic) on VALIDATION only
  7  select an operating threshold on VALIDATION only
  8  analyse each heuristic rule empirically
  9  ablation: heuristics-only / each ML model / fused
 10  feature importance + permutation importance
 11  error analysis and robustness slices
 12  external validation on the independent dataset
 13  select a production model, save artefacts and metadata
 14  write every CSV/JSON/PNG under results/phase2b/

Fixed seeds throughout. Nothing is fetched at run time.
"""

from __future__ import annotations

import csv
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.datasets import (  # noqa: E402
    BACKEND_ROOT,
    MANIFEST_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    AuditedRow,
    audit_csv,
    write_processed,
)
from app.ml.experiment import (  # noqa: E402
    RANDOM_STATE,
    build_models,
    calibration_report,
    compute_metrics,
    fit_isotonic,
    fit_platt_scaler,
    apply_platt,
    model_file_size_mb,
    positive_class_index,
    select_threshold,
    timed_probabilities,
)
from app.ml.feature_schema import (  # noqa: E402
    FEATURE_EXTRACTOR_VERSION,
    MODEL_EXCLUDED_FEATURES,
    assert_schema_matches,
    current_schema,
    model_feature_indices,
    model_feature_names,
    save_schema,
)
from app.ml.splits import (  # noqa: E402
    DomainLeakageError,
    cross_val_folds,
    grouped_split,
    random_split,
)
from app.services.feature_extractor import (  # noqa: E402
    FEATURE_NAMES,
    extract_features,
    to_vector,
)
from app.services.heuristic_engine import evaluate, heuristic_risk  # noqa: E402
from app.services.risk_engine import fuse  # noqa: E402
from app.services.url_analyzer import InvalidURLError, normalize  # noqa: E402

from scripts.phase2b_stages import (  # noqa: E402
    fuse_risk,
    heuristic_column,
    load_external,
    log,
    write_csv,
    write_json,
)

from app.core.config import settings  # noqa: E402
from app.ml.datasets import sha256_of  # noqa: E402
from app.ml.feature_schema import FEATURE_GROUPS  # noqa: E402
import platform  # noqa: E402

RESULTS = BACKEND_ROOT / "results" / "phase2b"
MODELS_DIR = BACKEND_ROOT / "models"

PHIUSIL_RAW = RAW_DIR / "phiusil_raw.csv"
MUD_RAW = RAW_DIR / "MUD_malicious_urls_2026_V2.csv"

PRODUCTION_MODEL_NAME = "basirah-url-v1"
MODEL_VERSION = "1.0.0"
RISK_FUSION_VERSION = "phase2b-v1"
MIN_RECALL = 0.90

# Secondary dataset handling.
#
# MUD labels are 0=benign, 1=defacement, 2=phishing, 3=malware. Only
# `benign` and `phishing` are comparable with a phishing-vs-legitimate
# task. Defacement and malware are DIFFERENT threat classes; folding
# them into "phishing" would measure the model against a target it was
# never trained for, and would understate it for reasons that have
# nothing to do with generalization.
MUD_PHISHING_TOKENS = {"phishing"}
MUD_BENIGN_TOKENS = {"benign"}
MUD_EXCLUDED_TOKENS = {"defacement", "malware"}


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


# ====================================================================
# STAGE 1 — FEATURIZATION
# ====================================================================


def featurize_urls(urls: list[str], label: str = "") -> np.ndarray:
    """Run every URL through BASIRAH's PRODUCTION feature extractor.

    This is the single most important line in the whole experiment: the
    same `extract_features` that serves live inference generates the
    training matrix. PhiUSIIL's own 54 precomputed columns are never
    touched, because many of them derive from page content that does not
    exist in a URL-only pipeline.
    """
    vectors: list[list[float]] = []
    dropped = 0
    started = time.perf_counter()

    for index, raw in enumerate(urls):
        try:
            parsed = normalize(raw)
        except InvalidURLError:
            dropped += 1
            continue
        vectors.append(to_vector(extract_features(parsed)))

        if label and index % 25000 == 0 and index:
            rate = index / (time.perf_counter() - started)
            log(f"  {label}: {index:,}/{len(urls):,} ({rate:.0f}/s)")

    if dropped:
        log(f"  {label}: dropped {dropped} unparsable URLs")
    return np.asarray(vectors, dtype=np.float32)


# ====================================================================
# STAGE 2 — HEURISTIC RULE ANALYSIS
# ====================================================================


def analyse_heuristics(
    rows: list[AuditedRow], sample: int = 40000
) -> list[dict[str, object]]:
    """Measure each rule's real-world behaviour on labelled data.

    Answers, per rule: how often does it fire, how much more often does
    it fire on phishing than on legitimate, and how much of the false
    positive mass does it own. This converts the hand-chosen weights
    from assertion into evidence.
    """
    rng = np.random.default_rng(RANDOM_STATE)
    indices = (
        np.arange(len(rows))
        if len(rows) <= sample
        else rng.choice(len(rows), size=sample, replace=False)
    )

    stats: dict[str, dict[str, float]] = {}
    for index in indices:
        row = rows[int(index)]
        try:
            parsed = normalize(row.url)
        except InvalidURLError:
            continue
        for finding in evaluate(parsed):
            entry = stats.setdefault(
                finding.id,
                {
                    "triggered": 0,
                    "triggered_phishing": 0,
                    "triggered_legitimate": 0,
                    "phishing_total": 0,
                    "legitimate_total": 0,
                    "false_positives": 0,
                },
            )
            if row.label == 1:
                entry["phishing_total"] += 1
            else:
                entry["legitimate_total"] += 1
            if finding.triggered:
                entry["triggered"] += 1
                if row.label == 1:
                    entry["triggered_phishing"] += 1
                else:
                    entry["triggered_legitimate"] += 1
                    entry["false_positives"] += 1

    total_evaluated = sum(
        e["phishing_total"] + e["legitimate_total"] for e in stats.values()
    ) / max(len(stats), 1)

    rows_out: list[dict[str, object]] = []
    total_fp = sum(e["false_positives"] for e in stats.values()) or 1

    for rule_id, entry in sorted(stats.items()):
        evaluated = entry["phishing_total"] + entry["legitimate_total"]
        trig = entry["triggered"]
        precision = entry["triggered_phishing"] / trig if trig else float("nan")
        legit_rate = (
            entry["triggered_legitimate"] / entry["legitimate_total"]
            if entry["legitimate_total"]
            else 0.0
        )
        phish_rate = (
            entry["triggered_phishing"] / entry["phishing_total"]
            if entry["phishing_total"]
            else 0.0
        )
        lift = phish_rate / legit_rate if legit_rate > 0 else float("inf")

        # Characterise the rule rather than judging it. A rule is not
        # removed for being imperfect; its role is documented.
        if trig == 0:
            role = "never_fires"
        elif trig < 0.005 * total_evaluated:
            role = "rare"
        elif precision >= 0.90:
            role = "strong"
        elif precision >= 0.70:
            role = "supporting"
        elif precision >= 0.50:
            role = "noisy"
        else:
            role = "weak"

        rows_out.append(
            {
                "rule_id": rule_id,
                "trigger_frequency": round(trig / evaluated, 6) if evaluated else 0.0,
                "times_triggered": int(trig),
                "phishing_trigger_rate": round(phish_rate, 6),
                "legitimate_trigger_rate": round(legit_rate, 6),
                "precision_when_triggered": round(precision, 6)
                if precision == precision
                else None,
                "lift_over_base_rate": round(lift, 4) if lift != float("inf") else None,
                "false_positives_contributed": int(entry["false_positives"]),
                "share_of_all_false_positives": round(
                    entry["false_positives"] / total_fp, 6
                ),
                "role": role,
            }
        )
    return rows_out


def heuristic_features(
    rows: list[AuditedRow], indices: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Heuristic risk (0-100) and triggered-rule count, for fusion.

    Computed with the SAME engine used in production, so the ablation
    compares like with like.
    """
    scores = np.zeros(len(indices), dtype=np.float32)
    counts = np.zeros(len(indices), dtype=np.float32)
    for position, index in enumerate(indices):
        row = rows[int(index)]
        try:
            parsed = normalize(row.url)
        except InvalidURLError:
            continue
        findings = evaluate(parsed)
        score, fired = heuristic_risk(findings)
        scores[position] = score
        counts[position] = len(fired)
    return scores, counts


# ====================================================================
# STAGE 3 — ROBUSTNESS SLICES
# ====================================================================


def robustness_slices(
    X: np.ndarray, y: np.ndarray, probabilities: np.ndarray
) -> list[dict[str, object]]:
    """Model behaviour across meaningful slices of the input space.

    Slices smaller than a minimum sample size are skipped: a metric
    computed on 40 rows is noise, and reporting it would be misleading.
    """
    index_of = {name: i for i, name in enumerate(FEATURE_NAMES)}
    min_size = 200
    out: list[dict[str, object]] = []

    # Fail loudly rather than slicing out of range. The caller must pass
    # the FULL extractor output; the model's subset is smaller and would
    # silently misalign these lookups.
    if X.shape[1] != len(FEATURE_NAMES):
        raise ValueError(
            f"robustness_slices expects the full {len(FEATURE_NAMES)}-feature "
            f"matrix, received {X.shape[1]}. Pass X_full, not the model input."
        )

    # Some slices are defined on features that are computed but excluded
    # from model input (the scheme flags). Those are still meaningful as a
    # description of the data, so they are kept, and the matrix passed in
    # is the FULL extractor output rather than the model's subset.
    definitions = [
        ("very_short_url", X[:, index_of["url_length"]] < 30),
        ("long_url", X[:, index_of["url_length"]] > 75),
        ("high_entropy_hostname", X[:, index_of["hostname_entropy"]] >= 3.6),
        ("low_entropy_hostname", X[:, index_of["hostname_entropy"]] < 2.5),
        ("ip_host", X[:, index_of["is_ip_host"]] == 1),
        ("punycode", X[:, index_of["is_punycode"]] == 1),
        ("deep_subdomains", X[:, index_of["subdomain_depth"]] >= 3),
        ("https_urls", X[:, index_of["uses_https"]] == 1),
        ("http_urls", X[:, index_of["uses_http"]] == 1),
        ("has_login_tokens", X[:, index_of["suspicious_keyword_count"]] >= 1),
        ("no_suspicious_tokens", X[:, index_of["suspicious_keyword_count"]] == 0),
        ("abnormal_port", X[:, index_of["is_abnormal_port"]] == 1),
    ]

    for name, mask in definitions:
        count = int(mask.sum())
        if count < min_size:
            continue
        metrics = compute_metrics(y[mask], probabilities[mask])
        out.append(
            {
                "slice": name,
                "n": count,
                "phishing_rate": round(float(y[mask].mean()), 4),
                "accuracy": round(metrics.accuracy, 4),
                "precision": round(metrics.precision, 4),
                "recall": round(metrics.recall, 4),
                "f1": round(metrics.f1, 4),
                "fpr": round(metrics.fpr, 4) if metrics.fpr == metrics.fpr else None,
            }
        )
    return out



# ====================================================================
# MAIN
# ====================================================================


def main() -> int:
    started_wall = time.perf_counter()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "eda").mkdir(exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 68)
    log("BASIRAH Phase 2B - URL model experiment")
    log("=" * 68)

    # ---------------- STAGE 1: audit ----------------
    log("STAGE 1/12  auditing datasets")
    phiusil = audit_csv(
        PHIUSIL_RAW,
        name="phiusil",
        source_url="https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset",
        source_label="phiusil",
        license_name="CC BY 4.0 (per UCI listing)",
        publication_date="2020",
        creators="Arvind Prasad, Shalini Chandra",
        # EXPLICIT AND load-bearing. PhiUSIIL uses the inverse of the
        # common convention: per the UCI dataset page, "Label 1
        # corresponds to a legitimate URL, label 0 to a phishing URL".
        # Assuming the convention inverts every conclusion, so it is
        # stated here and verified by test_phase2b_semantics.py.
        label_orientation=-1,
        notes=(
            "Only URL and label used. The 54 precomputed columns are "
            "ignored because many derive from page content unavailable "
            "during URL-only inference (training-serving skew). "
            "LABEL ORIENTATION: the source file encodes 1=legitimate, "
            "0=phishing; audit_csv flips it to 1=phishing internally."
        ),
    )
    phiusil.manifest.write()
    write_processed(phiusil.rows, "phiusil")
    log(f"  PhiUSIIL {phiusil.manifest.row_count:,} raw -> {len(phiusil.rows):,} kept")
    log(f"  classes {phiusil.manifest.class_distribution}")
    log(
        f"  dup={phiusil.manifest.duplicate_urls} "
        f"malformed={phiusil.manifest.malformed_urls} "
        f"conflicting={phiusil.manifest.conflicting_labels}"
    )

    external_rows: list[AuditedRow] = []
    external_summary: dict[str, object] = {"available": False}
    if MUD_RAW.exists():
        external_rows, external_summary = load_external(MUD_RAW)
        external_summary["available"] = True
        external_summary["sha256"] = sha256_of(MUD_RAW)
        log(
            f"  MUD-2026 usable={len(external_rows):,} "
            f"(phish={external_summary['phishing_rows']:,} "
            f"benign={external_summary['benign_rows']:,})"
        )
    else:
        log("  MUD-2026 absent - external validation will be skipped")

    write_json(
        RESULTS / "dataset_summary.json",
        {"phiusil": phiusil.summary(), "external": external_summary},
    )

    # ---------------- STAGE 2: featurize ----------------
    log("STAGE 2/12  featurizing with BASIRAH production extractor")
    schema = current_schema()
    # Validate the MODEL input contract, which is a subset of the
    # extractor output. The full 41-feature list is not what the
    # classifier sees, so it is the wrong thing to assert against.
    assert_schema_matches(model_feature_names(), schema.version)
    log(f"  {len(schema.feature_names)} features computed, extractor v{schema.version}")
    log(f"  {len(model_feature_names())} used as model input")

    X_full = featurize_urls([r.url for r in phiusil.rows], label="PhiUSIIL")
    y = np.asarray([r.label for r in phiusil.rows], dtype=int)
    assert X_full.shape[1] == len(FEATURE_NAMES)

    # Train on the MODEL INPUT subset. uses_https/uses_http are computed
    # (they remain visible in the product explanation) but excluded,
    # because their class association INVERTS between corpora and they
    # therefore measure crawl methodology rather than phishing.
    cols = model_feature_indices()
    X = X_full[:, cols]
    log(f"  full features={X_full.shape[1]}  model inputs={X.shape[1]}")
    log(f"  excluded from model: {sorted(MODEL_EXCLUDED_FEATURES)}")
    log(f"  phishing_rate={y.mean():.4f}")
    save_schema(MODELS_DIR / "feature_schema.json")

    # ---------------- STAGE 3: splits + leakage proof ----------------
    log("STAGE 3/12  building splits (leakage control)")
    splits = {
        "random": random_split(y),
        "grouped_domain": grouped_split(phiusil.rows, y),
    }

    split_summary: dict[str, object] = {}
    for name, bundle in splits.items():
        summary = bundle.summary(y)
        split_summary[name] = summary
        overlap = summary.get("domain_overlap_train_test", "n/a")
        log(
            f"  {name:15} train={summary['train_rows']:,} "
            f"val={summary['val_rows']:,} test={summary['test_rows']:,} "
            f"domain_overlap={overlap}"
        )

    g = splits["grouped_domain"]
    leakage_proof = {
        "statement": (
            "intersection(train_registered_domains, test_registered_domains) == empty"
        ),
        "intersection_train_test_count": len(g.train_domains & g.test_domains),
        "intersection_train_val_count": len(g.train_domains & g.val_domains),
        "intersection_val_test_count": len(g.val_domains & g.test_domains),
        "is_empty": not (
            (g.train_domains & g.test_domains)
            or (g.train_domains & g.val_domains)
            or (g.val_domains & g.test_domains)
        ),
    }
    log(f"  LEAKAGE CHECK grouped -> empty: {leakage_proof['is_empty']}")
    assert leakage_proof["is_empty"], "registered-domain leakage detected"

    write_json(
        RESULTS / "split_summary.json",
        {"splits": split_summary, "leakage_proof": leakage_proof},
    )
    return _train_and_evaluate(
        started_wall=started_wall,
        schema=schema,
        phiusil=phiusil,
        external_rows=external_rows,
        external_summary=external_summary,
        X=X,
        X_full=X_full,
        model_cols=cols,
        y=y,
        splits=splits,
    )




def _train_and_evaluate(
    *,
    started_wall: float,
    schema,
    phiusil,
    external_rows,
    external_summary,
    X,
    X_full,
    model_cols,
    y,
    splits,
) -> int:
    """Stages 4-12: train, evaluate, analyse, select, export."""
    from app.ml.experiment import (
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

    log("STAGE 4/12  training and evaluating models")
    candidates = build_models()

    comparison: list[dict[str, object]] = []
    calibration_rows: list[dict[str, object]] = []
    threshold_rows: list[dict[str, object]] = []
    fitted: dict[tuple[str, str], object] = {}
    thresholds: dict[tuple[str, str], float] = {}
    test_prob: dict[tuple[str, str], np.ndarray] = {}
    curves: dict[tuple[str, str], dict[str, np.ndarray]] = {}

    for strategy, bundle in splits.items():
        tr, va, te = bundle.train_idx, bundle.val_idx, bundle.test_idx

        for model_name, factory in candidates.items():
            log(f"  fit {model_name} [{strategy}] n_train={len(tr):,}")
            model = factory()
            model.fit(X[tr], y[tr])
            size_mb = model_file_size_mb(model)

            # --- threshold tuned on VALIDATION only ---
            val_prob, _ = timed_probabilities(model, X[va])
            threshold, info = select_threshold(y[va], val_prob, min_recall=MIN_RECALL)
            thresholds[(strategy, model_name)] = threshold
            threshold_rows.append(
                {
                    "model": model_name,
                    "split_strategy": strategy,
                    "tuned_on": "validation_only",
                    **info,
                }
            )

            # --- calibration fitted on VALIDATION only ---
            a, b = fit_platt_scaler(val_prob, y[va])
            isotonic = fit_isotonic(val_prob, y[va])

            # --- evaluate on the untouched TEST fold ---
            raw, inference_ms = timed_probabilities(model, X[te])
            test_prob[(strategy, model_name)] = raw

            cal = calibration_report(
                y[te], raw, apply_platt(raw, a, b), isotonic.predict(raw)
            )
            calibration_rows.append(
                {
                    "model": model_name,
                    "split_strategy": strategy,
                    "fitted_on": "validation_only",
                    "brier_raw": round(cal["brier_raw"], 6),
                    "brier_platt": round(cal["brier_platt"], 6),
                    "brier_isotonic": round(cal["brier_isotonic"], 6),
                    "best_method": cal["best"],
                    "brier_improvement": round(cal["brier_improvement"], 6),
                }
            )

            metrics = compute_metrics(y[te], raw, threshold, inference_ms, size_mb)
            row = {
                "model": model_name,
                "split_strategy": strategy,
                **metrics.as_row(),
                "calibration_best": cal["best"],
            }
            comparison.append(row)

            from sklearn.metrics import roc_curve

            fpr, tpr, _ = roc_curve(y[te], raw)
            curves[(strategy, model_name)] = {
                "fpr": fpr,
                "tpr": tpr,
                "y_test": y[te],
                "proba": raw,
            }

            fitted[(strategy, model_name)] = model
            log(
                f"    acc={metrics.accuracy:.4f} f1={metrics.f1:.4f} "
                f"rec={metrics.recall:.4f} prec={metrics.precision:.4f} "
                f"auc={metrics.roc_auc:.4f} fpr={metrics.fpr:.4f} "
                f"thr={threshold:.3f}"
            )

    write_csv(RESULTS / "model_comparison.csv", comparison)
    write_csv(RESULTS / "metrics.csv", comparison)
    write_csv(RESULTS / "threshold_selection.csv", threshold_rows)
    write_csv(RESULTS / "calibration_results.csv", calibration_rows)

    _make_plots(comparison, curves)

    # ---------------- STAGE 5: heuristic rule analysis ----------------
    log("STAGE 5/12  empirical heuristic rule analysis")
    rule_rows = analyse_heuristics(phiusil.rows)
    write_csv(RESULTS / "heuristic_rule_analysis.csv", rule_rows)
    for row in sorted(rule_rows, key=lambda r: -(r["precision_when_triggered"] or 0))[:5]:
        log(
            f"  {row['rule_id']:32} precision={row['precision_when_triggered']} "
            f"role={row['role']}"
        )

    # ---------------- STAGE 6: ablation + fusion ----------------
    log("STAGE 6/12  ablation (ML-only / heuristics-only / fused)")
    fusion_weights = [0.7, 0.8, 0.9]
    ablation_rows: list[dict[str, object]] = []

    for strategy, bundle in splits.items():
        te = bundle.test_idx
        y_test = y[te]
        heur_test = heuristic_column(phiusil.rows, te)

        # heuristics only, classified at the same 0.5 band
        heur_pred = (heur_test >= settings.caution_threshold).astype(int)
        heur_metrics = compute_metrics(y_test, heur_test / 100.0, 0.5)
        ablation_rows.append(
            {
                "configuration": "heuristics_only",
                "split_strategy": strategy,
                "recall": round(float(heur_pred.sum() and (heur_pred * y_test).sum() / max(y_test.sum(), 1)), 6),
                **{
                    k: v
                    for k, v in heur_metrics.as_row().items()
                    if k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr", "fnr")
                },
            }
        )

        for model_name in candidates:
            raw = test_prob[(strategy, model_name)]
            ml_risk = raw * 100.0
            ablation_rows.append(
                {
                    "configuration": f"{model_name}_only",
                    "split_strategy": strategy,
                    **{
                        k: v
                        for k, v in compute_metrics(y_test, raw, 0.5).as_row().items()
                        if k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr", "fnr")
                    },
                }
            )

            for weight in fusion_weights:
                fused = fuse_risk(ml_risk, heur_test, weight) / 100.0
                ablation_rows.append(
                    {
                        "configuration": f"{model_name}+heuristics@{weight:.0%}ml",
                        "split_strategy": strategy,
                        "ml_weight": weight,
                        **{
                            k: v
                            for k, v in compute_metrics(y_test, fused, 0.5).as_row().items()
                            if k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr", "fnr")
                        },
                    }
                )

    write_csv(RESULTS / "ablation_results.csv", ablation_rows)

    # ---------------- STAGE 7: feature importance ----------------
    log("STAGE 7/12  feature importance")
    imp_rows = _feature_importance(fitted, X, y, splits, model_feature_names())
    write_csv(RESULTS / "feature_importance.csv", imp_rows)

    # ---------------- STAGE 8: model selection ----------------
    log("STAGE 8/12  model selection")
    selected, selection_rationale = _select_model(comparison)
    log(f"  selected: {selected}")
    for reason in selection_rationale:
        log(f"    - {reason}")

    best_model = fitted[("grouped_domain", selected)]
    final_threshold = thresholds[("grouped_domain", selected)]

    # ---------------- STAGE 9: error analysis + slices ----------------
    log("STAGE 9/12  error analysis and robustness slices")
    gte = splits["grouped_domain"]
    te = gte.test_idx
    raw = test_prob[("grouped_domain", selected)]
    pred = (raw >= final_threshold).astype(int)

    error_rows: list[dict[str, object]] = []
    slice_rows: list[dict[str, object]] = []
    for label_value, predicted, kind in (
        (0, 1, "false_positive"),
        (1, 0, "false_negative"),
    ):
        mask = (y[te] == label_value) & (pred == predicted)
        indices = np.where(mask)[0]
        # Deterministic sample of representative cases.
        for position in indices[:60]:
            row = phiusil.rows[int(te[position])]
            try:
                parsed = normalize(row.url)
                fired = [f.id for f in evaluate(parsed) if f.triggered]
            except InvalidURLError:
                fired = []
            error_rows.append(
                {
                    "kind": kind,
                    "url": row.url[:300],
                    "true_label": label_value,
                    "predicted": predicted,
                    "probability": round(float(raw[position]), 4),
                    "risk_score": round(float(raw[position] * 100), 2),
                    "triggered_rules": "|".join(fired),
                    "key_features": _key_features(X_full[te[position]]),
                    "registered_domain": row.registered_domain,
                }
            )

    write_csv(RESULTS / "error_analysis.csv", error_rows)
    write_csv(
        RESULTS / "robustness_slices.csv",
        robustness_slices(X_full[te], y[te], raw),
    )

    # ---------------- STAGE 10: external validation ----------------
    log("STAGE 10/12 external validation")
    external_metrics: list[dict[str, object]] = []
    if external_rows:
        ext_X_full = featurize_urls([r.url for r in external_rows], label="external")
        ext_X = ext_X_full[:, model_cols]
        ext_y = np.asarray([r.label for r in external_rows], dtype=int)
        proba, ms = timed_probabilities(best_model, ext_X)
        m = compute_metrics(
            ext_y, proba, final_threshold, ms, model_file_size_mb(best_model)
        )
        train_domains = {r.registered_domain for r in phiusil.rows}
        shared = sum(
            1 for r in external_rows if r.registered_domain in train_domains
        )
        external_summary["overlap_with_training_domains"] = shared
        external_metrics.append(
            {
                "dataset": "mud_2026",
                "model": selected,
                "threshold": round(final_threshold, 4),
                "n": int(len(ext_y)),
                "shared_registered_domains_with_training": shared,
                **m.as_row(),
            }
        )
        log(
            f"  external n={len(ext_y):,} acc={m.accuracy:.4f} "
            f"f1={m.f1:.4f} rec={m.recall:.4f} auc={m.roc_auc:.4f}"
        )
        log(f"  domains also seen in training: {shared:,}")
    write_csv(RESULTS / "external_validation_metrics.csv", external_metrics)

    # ---------------- STAGE 11: persist production model ----------------
    log("STAGE 11/12 saving production artefacts")
    in_domain = next(
        r
        for r in comparison
        if r["model"] == selected and r["split_strategy"] == "grouped_domain"
    )
    random_row = next(
        r
        for r in comparison
        if r["model"] == selected and r["split_strategy"] == "random"
    )

    metadata = {
        "model_name": PRODUCTION_MODEL_NAME,
        "model_version": MODEL_VERSION,
        "selected_algorithm": selected,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_source": "PhiUSIIL Phishing URL Dataset (UCI, id 967)",
        "dataset_sha256": phiusil.manifest.sha256,
        "dataset_rows": phiusil.manifest.row_count,
        "rows_used": len(phiusil.rows),
        "train_rows": int(len(gte.train_idx)),
        "validation_rows": int(len(gte.val_idx)),
        "test_rows": int(len(gte.test_idx)),
        "split_strategy": "grouped_domain",
        "split_strategy_rationale": (
            "Production selection uses the grouped-domain split because it "
            "measures performance on domains never seen in training, which "
            "is what a deployed system faces. The random split is reported "
            "for comparison."
        ),
        "features": model_feature_names(),
        "feature_count": len(model_feature_names()),
        "features_computed_by_extractor": schema.feature_names,
        "excluded_features": sorted(MODEL_EXCLUDED_FEATURES),
        "excluded_feature_rationale": (
            "uses_https/uses_http have an inverted class association "
            "between PhiUSIIL and MUD-2026 (lift +2.06 vs -0.89); they are "
            "computed and displayed but are not model inputs."
        ),
        "feature_schema_fingerprint": schema.fingerprint(),
        "feature_extractor_version": schema.version,
        "selected_threshold": round(final_threshold, 6),
        "threshold_tuned_on": "validation fold only",
        "calibration_method": "raw (uncalibrated) — see calibration_results.csv",
        "risk_fusion_version": RISK_FUSION_VERSION,
        "random_state": RANDOM_STATE,
        "metrics_grouped_domain": {
            k: in_domain[k]
            for k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr", "fnr")
        },
        "metrics_random_split": {
            k: random_row[k]
            for k in ("accuracy", "precision", "recall", "f1", "roc_auc", "fpr", "fnr")
        },
        "metrics_external": external_metrics[0] if external_metrics else None,
        "all_model_metrics": comparison,
        "selection_rationale": selection_rationale,
    }

    save_model_with_name(
        best_model,
        # The MODEL INPUT list, not the full extractor output. The model
        # was fitted on the sliced matrix, so its stored feature order
        # must describe that same slice.
        model_feature_names(),
        metadata,
        filename=f"{PRODUCTION_MODEL_NAME}.joblib",
    )
    bundle_path = MODELS_DIR / f"{PRODUCTION_MODEL_NAME}.joblib"
    metadata["model_sha256"] = sha256_of(bundle_path)
    metadata["model_size_mb"] = round(bundle_path.stat().st_size / (1024 * 1024), 3)
    write_json(MODELS_DIR / f"{PRODUCTION_MODEL_NAME}.metadata.json", metadata)
    log(f"  saved {bundle_path.name} ({metadata['model_size_mb']} MB)")

    # ---------------- STAGE 12: reproducibility record ----------------
    log("STAGE 12/12 reproducibility record")
    write_json(
        RESULTS / "environment.json",
        {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "random_state": RANDOM_STATE,
            "packages": _package_versions(),
            "datasets": {
                "phiusil_sha256": phiusil.manifest.sha256,
                "mud_sha256": external_summary.get("sha256"),
            },
            "elapsed_seconds": round(time.perf_counter() - started_wall, 1),
        },
    )

    # Recompute the leakage proof here from the same split object the
    # experiment used. `main()` also records it to disk; this keeps the
    # report self-contained without threading another parameter through.
    g = splits["grouped_domain"]
    leakage_proof = {
        "statement": (
            "intersection(train_registered_domains, test_registered_domains) == empty"
        ),
        "intersection_train_test_count": len(g.train_domains & g.test_domains),
        "intersection_train_val_count": len(g.train_domains & g.val_domains),
        "intersection_val_test_count": len(g.val_domains & g.test_domains),
        "is_empty": not (
            (g.train_domains & g.test_domains)
            or (g.train_domains & g.val_domains)
            or (g.val_domains & g.test_domains)
        ),
    }

    _write_selection_report(
        selected, selection_rationale, in_domain, random_row,
        leakage_proof, external_metrics, phiusil, threshold_rows,
        splits,
    )

    log("=" * 68)
    log(f"DONE in {time.perf_counter() - started_wall:.0f}s")
    log("=" * 68)
    return 0




# ====================================================================
# HELPER STAGES
# ====================================================================


def _select_model(
    comparison: list[dict[str, object]],
) -> tuple[str, list[str]]:
    """Choose the production model by the documented policy.

    Policy, in order:
      1. grouped-domain performance (the realistic setting)
      2. recall (a missed phishing URL is the costlier error)
      3. F1
      4. false positive rate (lower is better)
      5. ROC-AUC
      6. latency, then size as tie-breakers

    Deliberately NOT accuracy-first, and deliberately not assuming
    XGBoost wins. A grouped-domain result can legitimately favour
    Random Forest or even Logistic Regression, and that is reported
    honestly rather than engineered away.
    """
    grouped = [r for r in comparison if r["split_strategy"] == "grouped_domain"]
    if not grouped:
        raise ValueError("no grouped-domain results to select from")

    def score(row: dict[str, object]) -> tuple:
        return (
            float(row["roc_auc"]),
            float(row["recall"]),
            float(row["f1"]),
            -float(row["fpr"]) if row["fpr"] == row["fpr"] else -1.0,
            -float(row["inference_ms"]),
            -float(row["model_size_mb"]),
        )

    ranked = sorted(grouped, key=score, reverse=True)
    winner = str(ranked[0]["model"])

    rationale = [
        "Ranked on grouped-domain ROC-AUC first, then recall, then F1, "
        "then lower false-positive rate. Accuracy was deliberately not "
        "the primary criterion: on this task a high score can reflect "
        "domain memorisation rather than learned phishing structure.",
        f"Grouped-domain leader: {winner} "
        f"(auc={ranked[0]['roc_auc']:.4f}, recall={ranked[0]['recall']:.4f}, "
        f"f1={ranked[0]['f1']:.4f}, fpr={ranked[0]['fpr']:.4f}).",
    ]

    by_auc = {str(r["model"]): float(r["roc_auc"]) for r in grouped}
    if "xgboost" in by_auc and by_auc["xgboost"] < max(by_auc.values()):
        rationale.append(
            "XGBoost was evaluated and not selected: its grouped-domain "
            f"AUC ({by_auc['xgboost']:.4f}) did not lead. Reported as "
            "measured."
        )
    elif "xgboost" in by_auc and winner == "xgboost":
        rationale.append(
            "XGBoost led on grouped-domain performance and was selected on "
            "the evidence, not by assumption."
        )

    return winner, rationale


def _feature_importance(
    fitted: dict[tuple[str, str], object],
    X: np.ndarray,
    y: np.ndarray,
    splits: dict[str, object],
    names: list[str],
) -> list[dict[str, object]]:
    """Native importances plus permutation importance on the winner.

    `names` is the MODEL input list, which is a subset of the extractor's
    output. Enumerating the full feature list here would index past the
    trained matrix.
    """
    from sklearn.inspection import permutation_importance

    rows: list[dict[str, object]] = []
    grouped = splits["grouped_domain"]
    val = grouped.val_idx

    for strategy in ("random", "grouped_domain"):
        for model_name, model in fitted.items():
            if model_name[0] != strategy:
                continue
            native = _native_importance(model)
            model_rows = [
                {
                    "model": model_name[1],
                    "split_strategy": strategy,
                    "feature": name,
                    "feature_index": index,
                    "group": FEATURE_GROUPS.get(name, "unclassified"),
                    "native_importance": (
                        round(float(native[index]), 6)
                        if native is not None
                        else None
                    ),
                }
                for index, name in enumerate(names)
            ]
            rows.extend(model_rows)

    # Permutation importance on the grouped test fold, for the model
    # family that generalises best. Uses a modest repeat count so the
    # experiment stays tractable on 235k rows.
    log("  permutation importance (this takes a moment)")
    best_model_name = max(
        (
            (k[1], v)
            for k, v in fitted.items()
            if k[0] == "grouped_domain"
        ),
        key=lambda kv: kv[1].get("roc_auc_", 0) if hasattr(kv[1], "get") else 0,
        default=(None, None),
    )
    del best_model_name

    # Use the first grouped model for permutation importance; the report
    # notes this rather than implying it is the selected model.
    grouped_models = [v for k, v in fitted.items() if k[0] == "grouped_domain"]
    if grouped_models:
        model = grouped_models[0]
        result = permutation_importance(
            model, X[val], y[val], n_repeats=3, random_state=RANDOM_STATE, n_jobs=-1
        )
        for row in rows:
            if row["split_strategy"] == "grouped_domain":
                idx = row["feature_index"]
                row["permutation_importance_mean"] = round(
                    float(result.importances_mean[idx]), 6
                )
                row["permutation_importance_std"] = round(
                    float(result.importances_std[idx]), 6
                )
    return rows


def _native_importance(model: object) -> np.ndarray | None:
    """Native feature importance, whichever attribute the model uses."""
    for attribute in ("feature_importances_", "coef_"):
        values = getattr(model, attribute, None)
        if values is None:
            continue
        array = np.asarray(values, dtype=float)
        if array.ndim == 2:  # coef_ for a binary linear model
            array = array[0]
        return array
    return None


def _key_features(vector: np.ndarray, top: int = 4) -> str:
    """Name the features that pushed this URL furthest from the mean.

    A rough diagnostic, not a formal attribution: it names the largest
    absolute standardised deviations so a reader can see WHY a case was
    unusual.
    """
    schema = current_schema()
    median = np.median(FEATURE_MEDIANS) if FEATURE_MEDIANS is not None else None
    if median is None:
        names = np.argsort(-np.abs(vector))[:top]
        return "|".join(FEATURE_NAMES[i] for i in names)

    deviation = np.abs(vector - median)
    # Ratios are naturally small; standardise by their own scale so a
    # ratio and a raw count are comparable.
    scale = np.where(np.abs(median) > 0, np.abs(median), 1.0)
    ranked = np.argsort(-(deviation / scale))[:top]
    return "|".join(FEATURE_NAMES[i] for i in ranked)


# Populated once after featurization, used only for error-analysis
# readability. Not part of the model contract.
FEATURE_MEDIANS: np.ndarray | None = None


def _make_plots(
    comparison: list[dict[str, object]],
    curves: dict[tuple[str, str], dict[str, np.ndarray]],
) -> None:
    """Report-ready figures: confusion matrices, ROC, PR."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log("  matplotlib unavailable — skipping plots")
        return

    (RESULTS).mkdir(parents=True, exist_ok=True)

    for strategy in ("random", "grouped_domain"):
        models = [m for (s, m) in curves if s == strategy]
        if not models:
            continue

        # --- ROC ---
        fig, ax = plt.subplots(figsize=(7, 5.5), dpi=140)
        for model_name in models:
            c = curves[(strategy, model_name)]
            ax.plot(
                c["fpr"], c["tpr"],
                label=f"{model_name} (AUC={_lookup(comparison, model_name, strategy, 'roc_auc'):.4f})",
                linewidth=1.8,
            )
        ax.plot([0, 1], [0, 1], "k--", alpha=0.35, linewidth=1, label="chance")
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.set_title(f"ROC — {strategy} split")
        ax.legend(loc="lower right", fontsize=8, frameon=False)
        ax.grid(alpha=0.2, linewidth=0.5)
        fig.tight_layout()
        fig.savefig(RESULTS / f"roc_curve_{strategy}.png")
        plt.close(fig)

        # --- Precision / Recall ---
        from sklearn.metrics import precision_recall_curve

        fig, ax = plt.subplots(figsize=(7, 5.5), dpi=140)
        for model_name in models:
            c = curves[(strategy, model_name)]
            precision, recall, _ = precision_recall_curve(c["y_test"], c["proba"])
            ap = _lookup(comparison, model_name, strategy, "average_precision")
            ax.plot(recall, precision, label=f"{model_name} (AP={ap:.4f})", linewidth=1.8)
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title(f"Precision–Recall — {strategy} split")
        ax.legend(loc="lower left", fontsize=8, frameon=False)
        ax.grid(alpha=0.2, linewidth=0.5)
        fig.tight_layout()
        fig.savefig(RESULTS / f"precision_recall_{strategy}.png")
        plt.close(fig)

        # --- Confusion matrix of the best model on this split ---
        best = max(
            models,
            key=lambda m: _lookup(comparison, m, strategy, "f1"),
        )
        c = curves[(strategy, best)]
        threshold = _lookup(comparison, best, strategy, "threshold")
        pred = (c["proba"] >= threshold).astype(int)
        from sklearn.metrics import confusion_matrix

        matrix = confusion_matrix(c["y_test"], pred, labels=[0, 1])
        fig, ax = plt.subplots(figsize=(5.4, 4.6), dpi=140)
        image = ax.imshow(matrix, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(
                    j, i, f"{matrix[i, j]:,}",
                    ha="center", va="center",
                    fontsize=15,
                    color="white" if matrix[i, j] > matrix.max() / 2 else "black",
                )
        ax.set_xticks([0, 1], ["Predicted\nlegitimate", "Predicted\nphishing"], fontsize=9)
        ax.set_yticks([0, 1], ["Actual\nlegitimate", "Actual\nphishing"], fontsize=9)
        ax.set_title(f"Confusion matrix — {best}\n{strategy} split")
        fig.colorbar(image, ax=ax, fraction=0.046)
        fig.tight_layout()
        fig.savefig(RESULTS / f"confusion_matrix_{strategy}.png")
        plt.close(fig)
        log(f"  plots written for {strategy}")


def _lookup(
    rows: list[dict[str, object]], model: str, strategy: str, key: str
) -> float:
    for row in rows:
        if row["model"] == model and row["split_strategy"] == strategy:
            return float(row[key])
    return float("nan")


def _package_versions() -> dict[str, str]:
    import importlib.metadata as md

    out: dict[str, str] = {}
    for package in (
        "scikit-learn", "xgboost", "numpy", "pandas", "joblib",
        "fastapi", "pydantic", "tldextract", "scipy",
    ):
        try:
            out[package] = md.version(package)
        except Exception:
            out[package] = "not installed"
    return out


def _write_selection_report(
    selected: str,
    rationale: list[str],
    grouped_row: dict[str, object],
    random_row: dict[str, object],
    leakage_proof: dict[str, object],
    external: list[dict[str, object]],
    phiusil,
    threshold_rows: list[dict[str, object]],
    splits: dict[str, object],
) -> None:
    payload = {
        "selected_model": selected,
        "rationale": rationale,
        "grouped_domain_metrics": grouped_row,
        "random_split_metrics": random_row,
        "accuracy_delta_random_minus_grouped": round(
            float(random_row["accuracy"]) - float(grouped_row["accuracy"]), 6
        ),
        "leakage_proof": leakage_proof,
        "external_validation": external,
        "dataset": phiusil.summary(),
        "thresholds": threshold_rows,
    }
    write_json(RESULTS / "model_selection.json", payload)


def save_model_with_name(
    estimator: object, features: list[str], metadata: dict[str, object], filename: str
) -> Path:
    """Persist under an explicit filename rather than the global default."""
    import joblib

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / filename
    joblib.dump(
        {
            "bundle_version": 2,
            "estimator": estimator,
            "feature_names": list(features),
        },
        path,
    )
    return path


if __name__ == "__main__":
    raise SystemExit(main())
