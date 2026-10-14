"""
Phase 2E stages: reusable pieces for the URL-hardening experiment.

Everything the orchestrator needs that is not orchestration lives here:
the per-domain cap, the HTTPS bias table, matched-FPR recall, the scheme
split, the path-bias table, calibration evaluation, and the
heuristics/ML/fused ablation.

Splitting it out keeps `run_phase2e_experiment.py` readable as a stage
list, which is the only way a 17-artifact run stays auditable.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

import numpy as np

from app.ml.datasets import LEGITIMATE, PHISHING, AuditedRow
from app.services.feature_extractor import FEATURE_NAMES
from app.services.heuristic_engine import evaluate
from app.services.url_analyzer import InvalidURLError, normalize

BACKEND_PHASE2E = "phase2e"

# The four operating points the brief requires. Recall at a MATCHED FPR
# is the comparable quantity across models with wildly different score
# distributions: v1 outputs probabilities compressed near 1.0, so its
# "threshold" means nothing next to v3's, but its ROC is the same object.
MATCHED_FPR_TARGETS = (0.01, 0.03, 0.05, 0.10)

# Phase 2D established the path-bias fix: legitimate URLs were 0%
# path-bearing in PhiUSIIL, which made "has a path" a class proxy and
# broke real-world false positives. This is the shape the fix must
# preserve. Phase 2E re-measures it and refuses to promote a model whose
# legitimate-class mean probability at depth 0 rises back toward the
# phishing-class level.
PATH_BIAS_LEGIT_DEPTH0_MAX_MEAN_PROB = 0.35

# A heuristic rule is folded into the fused arm only when it is right at
# least this often on the rows it fires on. Measured rather than assumed:
# the Phase 2E rules fire on ~14% of legitimate test rows, so an
# unconditional OR fusion is strictly worse than the model alone.
HEURISTIC_FUSION_PRECISION_FLOOR = 0.90


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


# ====================================================================
# PER-DOMAIN CAP
# ====================================================================


def apply_domain_cap(
    rows: Sequence[AuditedRow], cap: int | None
) -> list[AuditedRow]:
    """Keep at most `cap` rows per registered domain, in input order.

    Deterministic by construction: no seed, so a rerun on the same
    corpus reproduces the same sample and a diff against
    `datasets/processed/` is meaningful. C22 re-derives this bound from
    the returned rows, so a bug here fails the gate rather than passing
    silently.

    Applied AFTER training and holdout exclusions, never before. Capping
    first would spend the budget on rows that are about to be discarded
    for leakage, leaving the retained rows thinner than the cap claims.
    """
    if cap is None:
        return list(rows)
    counts: Counter = Counter()
    kept: list[AuditedRow] = []
    for row in rows:
        if counts[row.registered_domain] >= cap:
            continue
        counts[row.registered_domain] += 1
        kept.append(row)
    return kept


def cap_report(rows: Sequence[AuditedRow], cap: int | None) -> dict[str, Any]:
    """What a cap does to this row set, measured rather than assumed."""
    counts = Counter(r.registered_domain for r in rows)
    total = len(rows)
    top = counts.most_common(10)
    return {
        "per_domain_cap": cap,
        "rows": total,
        "distinct_registered_domains": len(counts),
        "domains_per_row": round(len(counts) / max(total, 1), 6),
        "max_rows_per_domain": max(counts.values()) if counts else 0,
        "top_1_share": round(counts.most_common(1)[0][1] / max(total, 1), 6)
        if counts
        else 0.0,
        "top_10_share": round(sum(c for _, c in top) / max(total, 1), 6),
        "top_10_domains": top,
        "legitimate_rows": sum(1 for r in rows if r.label == LEGITIMATE),
        "phishing_rows": sum(1 for r in rows if r.label == PHISHING),
        "https_legitimate_share": round(
            sum(1 for r in rows if r.label == LEGITIMATE and r.uses_https)
            / max(sum(1 for r in rows if r.label == LEGITIMATE), 1),
            6,
        ),
    }


# ====================================================================
# HTTPS BIAS STUDY
# ====================================================================


def https_bias_table(rows_by_corpus: dict[str, Sequence[AuditedRow]]) -> list[dict[str, Any]]:
    """P(HTTPS | legitimate) vs P(HTTPS | phishing), per corpus.

    The Phase 2B evidence for excluding uses_https/uses_http from model
    input was that this quantity INVERTS between corpora: +2.06 lift on
    PhiUSIIL (where phishing is 100% HTTPS) against -0.89 on MUD 2026
    (where phishing is less HTTPS'd than legitimate). A feature whose
    class association flips sign with the collection method is measuring
    the crawler, not the attack.

    Re-measuring it for every corpus including the new one is the only
    way to know whether the Phase 2E addition changes that verdict,
    rather than inheriting it.
    """
    out: list[dict[str, Any]] = []
    for corpus in sorted(rows_by_corpus):
        rows = rows_by_corpus[corpus]
        legit = [r for r in rows if r.label == LEGITIMATE]
        phish = [r for r in rows if r.label == PHISHING]
        p_legit = sum(1 for r in legit if r.uses_https) / max(len(legit), 1)
        p_phish = sum(1 for r in phish if r.uses_https) / max(len(phish), 1)
        if not legit or not phish:
            lift = float("nan")
        elif p_legit == 0:
            lift = float("inf")
        else:
            lift = p_phish / p_legit
        out.append(
            {
                "corpus": corpus,
                "legitimate_rows": len(legit),
                "phishing_rows": len(phish),
                "p_https_given_legitimate": round(p_legit, 6),
                "p_https_given_phishing": round(p_phish, 6),
                "https_lift_phishing_over_legitimate": (
                    round(lift, 6) if lift == lift and lift != float("inf") else None
                ),
                "https_lift_interpretation": _lift_interpretation(lift),
                "gap": round(p_phish - p_legit, 6),
            }
        )
    return out


def _lift_interpretation(lift: float) -> str:
    if lift != lift:
        return "not measurable (one class absent)"
    if lift == float("inf"):
        return "degenerate: legitimate has no HTTPS rows at all"
    if lift > 1.5:
        return (
            "HTTPS positively associated with phishing in this corpus; the "
            "signal is a collection artefact unless it holds in every corpus"
        )
    if lift < 0.67:
        return (
            "HTTPS negatively associated with phishing in this corpus — the "
            "OPPOSITE direction to a +2.06 lift elsewhere, which is exactly "
            "the inversion that got the feature excluded"
        )
    return "no strong scheme-class association in this corpus"


def scheme_split_metrics(
    y: np.ndarray,
    probabilities: np.ndarray,
    rows: Sequence[AuditedRow],
    threshold: float,
) -> list[dict[str, Any]]:
    """Metrics computed separately over HTTPS and plain-HTTP test rows.

    A model can report one strong overall AUC while being completely
    blind on one scheme — and if the scheme features are candidates for
    re-inclusion, the split is the only view that shows whether they buy
    anything or merely sharpen the majority scheme.
    """
    from sklearn.metrics import roc_auc_score

    schemes = np.array(["https" if r.uses_https else "http" for r in rows])
    out: list[dict[str, Any]] = []
    for scheme in ("https", "http"):
        mask = schemes == scheme
        n = int(mask.sum())
        if n == 0:
            out.append(
                {
                    "scheme": scheme, "n": 0, "roc_auc": None,
                    "phishing_rate": None, "mean_probability": None,
                    "recall_at_threshold": None, "note": "no rows in this scheme",
                }
            )
            continue
        y_sub = y[mask]
        p_sub = probabilities[mask]
        try:
            auc = float(roc_auc_score(y_sub, p_sub))
        except ValueError:
            auc = None
        positives = y_sub == PHISHING
        recall = (
            float((p_sub[positives] >= threshold).mean()) if positives.any() else None
        )
        out.append(
            {
                "scheme": scheme,
                "n": n,
                "roc_auc": round(auc, 6) if auc is not None else None,
                "phishing_rate": round(float(y_sub.mean()), 6),
                "mean_probability": round(float(p_sub.mean()), 6),
                "recall_at_threshold": round(recall, 6) if recall is not None else None,
                "note": "",
            }
        )
    return out


# ====================================================================
# MATCHED-FPR RECALL
# ====================================================================


def recall_at_matched_fpr(
    negative_scores: np.ndarray,
    positive_scores: np.ndarray,
    targets: Sequence[float] = MATCHED_FPR_TARGETS,
) -> list[dict[str, Any]]:
    """Phishing recall at a fixed false-positive rate on legitimate URLs.

    The threshold is the (1 - target) quantile of the NEGATIVE score
    distribution, so it is derived from legitimate traffic alone and is
    then applied unchanged to phishing traffic. That is what makes it
    comparable across models whose absolute scores are not on a common
    scale — v1 saturates near 1.0, v3 centres near 0.5, and comparing
    their shipped thresholds measures their calibration rather than
    their ability to separate.

    Reported with the achievable FPR at that quantile, because quantile
    interpolation on a finite negative sample means the nominal target
    is not always exactly attainable and pretending otherwise would
    inflate the recall number.
    """
    out: list[dict[str, Any]] = []
    n_neg = len(negative_scores)
    n_pos = len(positive_scores)
    if n_neg == 0 or n_pos == 0:
        return [
            {
                "target_fpr": t, "threshold": None, "achieved_fpr": None,
                "recall": None, "false_positives": None, "false_negatives": None,
                "n_legitimate": n_neg, "n_phishing": n_pos,
                "note": "no negatives or no positives",
            }
            for t in targets
        ]

    for target in targets:
        threshold = float(np.quantile(negative_scores, 1.0 - target))
        fp = int((negative_scores >= threshold).sum())
        tp = int((positive_scores >= threshold).sum())
        out.append(
            {
                "target_fpr": round(target, 6),
                "threshold": round(threshold, 6),
                "achieved_fpr": round(fp / n_neg, 6),
                "recall": round(tp / n_pos, 6),
                "false_positives": fp,
                "false_negatives": n_pos - tp,
                "n_legitimate": n_neg,
                "n_phishing": n_pos,
                "note": "",
            }
        )
    return out


# ====================================================================
# PATH BIAS
# ====================================================================


def path_depth(normalized: str) -> int:
    """Number of non-empty path segments."""
    after_scheme = normalized.split("://", 1)[-1]
    _, _, remainder = after_scheme.partition("/")
    path_part = remainder or ""
    if "?" in path_part:
        path_part, _, _ = path_part.partition("?")
    return len([s for s in path_part.split("/") if s])


def path_bias_table(
    y: np.ndarray, probabilities: np.ndarray, rows: Sequence[AuditedRow]
) -> list[dict[str, Any]]:
    """Mean predicted probability by (label, path depth).

    The Phase 2D defect was legible in exactly this table: legitimate
    rows at depth 0 scored ~0.08 while phishing rows at depth 0 scored
    far higher, meaning the model had learned 'a path means phishing'.
    If the legitimate depth-0 mean climbs back toward the phishing
    depth-0 mean, the fix has regressed no matter what the AUC says.
    """
    buckets: dict[tuple[str, int], list[float]] = defaultdict(list)
    for index, row in enumerate(rows):
        label = "phishing" if int(y[index]) == PHISHING else "legitimate"
        buckets[(label, path_depth(row.normalized))].append(float(probabilities[index]))

    out: list[dict[str, Any]] = []
    for (label, depth), values in sorted(buckets.items()):
        ordered = sorted(values)
        out.append(
            {
                "label": label,
                "path_depth": depth,
                "n": len(values),
                "mean_probability": round(sum(values) / len(values), 6),
                "median_probability": round(ordered[len(ordered) // 2], 6),
                "flag_rate_at_threshold": None,  # filled by caller if wanted
            }
        )
    return out


def path_bias_verdict(
    table: Sequence[dict[str, Any]], phase2d_reference: dict[int, float]
) -> dict[str, Any]:
    """Did the Phase 2D path-bias fix survive adding the new corpus?

    Compares the legitimate depth-0 mean probability against both an
    absolute ceiling and the Phase 2D measured value, so a regression is
    detectable even if it does not cross the absolute ceiling.
    """
    legit0 = next(
        (r for r in table if r["label"] == "legitimate" and r["path_depth"] == 0), None
    )
    phish0 = next(
        (r for r in table if r["label"] == "phishing" and r["path_depth"] == 0), None
    )
    legit_mean = legit0["mean_probability"] if legit0 else float("nan")
    phish_mean = phish0["mean_probability"] if phish0 else float("nan")
    reference = phase2d_reference.get(0)
    passed = legit_mean == legit_mean and legit_mean <= PATH_BIAS_LEGIT_DEPTH0_MAX_MEAN_PROB
    delta = (
        round(legit_mean - reference, 6)
        if reference is not None and legit_mean == legit_mean
        else None
    )
    return {
        "legitimate_depth0_mean_probability": legit_mean,
        "phishing_depth0_mean_probability": phish_mean,
        "phase2d_legitimate_depth0_mean_probability": reference,
        "delta_vs_phase2d": delta,
        "absolute_ceiling": PATH_BIAS_LEGIT_DEPTH0_MAX_MEAN_PROB,
        "regressed_vs_phase2d": (
            bool(delta is not None and delta > 0.05)
        ),
        "passed": bool(passed),
        "interpretation": (
            "legitimate bare-host URLs still score far below phishing bare-host "
            "URLs, so 'has a path' has NOT become a class proxy again"
            if passed
            else "legitimate depth-0 URLs are scoring too high; the path-bias "
            "fix has regressed regardless of headline AUC"
        ),
    }


# ====================================================================
# HEURISTICS / ML / FUSED ABLATION
# ====================================================================


def heuristic_fire_vector(rows: Sequence[AuditedRow]) -> np.ndarray:
    """1.0 where any heuristic rule fired, 0.0 otherwise."""
    out = np.zeros(len(rows), dtype=np.float32)
    for index, row in enumerate(rows):
        try:
            parsed = normalize(row.url)
        except InvalidURLError:
            continue
        if any(finding.triggered for finding in evaluate(parsed)):
            out[index] = 1.0
    return out


def ablation_rows(
    y: np.ndarray,
    probabilities: np.ndarray,
    heuristic_fire: np.ndarray,
    threshold: float,
) -> list[dict[str, Any]]:
    """Three arms, evaluated on the same rows with the same threshold.

    Fused is OR, not a weighted average: a weighted blend would need a
    second tuned parameter fitted on the same data, and the honest
    question here is whether the heuristic engine adds detections the
    model misses, not whether a mixture weight can be tuned.
    """
    from sklearn.metrics import roc_auc_score

    ml = (probabilities >= threshold).astype(int)
    heur = heuristic_fire.astype(int)
    fused = np.maximum(ml, heur).astype(int)
    heuristic_scores = heuristic_fire.astype(float)

    out: list[dict[str, Any]] = []
    for arm, predictions, scores in (
        ("heuristics_only", heur, heuristic_scores),
        ("ml_only", ml, probabilities),
        ("fused_ml_or_heuristics", fused, np.maximum(probabilities, heuristic_scores)),
    ):
        matrix_pos = y == PHISHING
        matrix_neg = y == LEGITIMATE
        try:
            auc = float(roc_auc_score(y, scores))
        except ValueError:
            auc = float("nan")
        fp = int(predictions[matrix_neg].sum())
        fn = int((predictions[matrix_pos] == 0).sum())
        out.append(
            {
                "arm": arm,
                "n": len(y),
                "threshold": round(threshold, 6),
                "false_positives": fp,
                "false_negatives": fn,
                "fpr": round(fp / max(int(matrix_neg.sum()), 1), 6),
                "recall": round(
                    int((predictions[matrix_pos] == 1).sum())
                    / max(int(matrix_pos.sum()), 1),
                    6,
                ),
                "roc_auc": round(auc, 6) if auc == auc else None,
            }
        )
    return out


# ====================================================================
# FEATURE NAME -> COLUMN INDEX
# ====================================================================


def columns_for_feature_names(names: Sequence[str]) -> list[int]:
    """Map a model's declared feature names onto extractor columns.

    Deliberately by NAME, not by the position they occupy in
    `model_feature_names()`. v3's metadata lists `is_abnormal_port`
    last while the extractor's canonical order places it elsewhere, so
    positional slicing would feed v3 a permuted vector and produce
    confident nonsense — the exact failure mode
    `feature_schema.assert_schema_matches` exists to prevent.
    """
    lookup = {name: index for index, name in enumerate(FEATURE_NAMES)}
    missing = [name for name in names if name not in lookup]
    if missing:
        raise KeyError(
            f"Model declares features the live extractor does not produce: "
            f"{missing}. Refusing to score it."
        )
    return [lookup[name] for name in names]


def probability_of(
    estimator: object, matrix: np.ndarray
) -> np.ndarray:
    """predict_proba[:, 1] with the positive column read, not assumed."""
    classes = list(getattr(estimator, "classes_", [0, 1]))
    column = classes.index(1) if 1 in classes else len(classes) - 1
    return estimator.predict_proba(matrix)[:, column]  # type: ignore[attr-defined]


def score_urls(
    estimator: object, columns: Sequence[int], urls: Iterable[str]
) -> list[dict[str, Any]]:
    """Score a handful of URLs one at a time, with their features."""
    from app.services.feature_extractor import extract_features, to_vector

    out: list[dict[str, Any]] = []
    for url in urls:
        try:
            parsed = normalize(url)
        except InvalidURLError:
            out.append({"url": url, "probability": None, "error": "unparsable"})
            continue
        full = to_vector(extract_features(parsed))
        vector = [full[i] for i in columns]
        probabilities = estimator.predict_proba([vector])  # type: ignore[attr-defined]
        classes = list(getattr(estimator, "classes_", [0, 1]))
        column = classes.index(1) if 1 in classes else len(classes) - 1
        out.append(
            {
                "url": url,
                "probability": round(float(probabilities[0][column]), 6),
                "path_depth": path_depth(parsed.normalized),
                "query_param_count": full[FEATURE_NAMES.index("query_param_count")],
                "subdomain_depth": full[FEATURE_NAMES.index("subdomain_depth")],
                "registered_domain": parsed.registered_domain or parsed.hostname,
                "scheme": parsed.scheme,
            }
        )
    return out


def triggered_heuristics(url: str) -> str:
    try:
        parsed = normalize(url)
    except InvalidURLError:
        return "unparsable"
    return "|".join(f.id for f in evaluate(parsed) if f.triggered) or "none"