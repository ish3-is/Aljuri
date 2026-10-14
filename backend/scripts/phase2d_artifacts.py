"""
Produce the Phase 2D analysis artifacts the run did not write.

The pipeline established the headline result (v1 10/14 -> candidate 5/14,
with the recall comparison corrected to a matched-FPR basis) and wrote a
v3 candidate bundle. It did not emit the per-category, per-error and
path-bias breakdowns the phase specification requires.

Everything here is DERIVED from artefacts already on disk plus one
recomputation that reloads the saved candidate bundle. Nothing is
retrained, and no existing result is overwritten.
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
RESULTS = BACKEND / "results" / "phase2d"
CANDIDATE = BACKEND / "models" / "basirah-url-v3.joblib"

# Categories used by the Phase 2C curated set, so Phase 2D's per-category
# breakdown speaks the same vocabulary as the existing regression suite.
CATEGORY_BY_HOST = {
    "github.com": "repository", "gitlab.com": "repository",
    "docs.python.org": "documentation",
    "developer.mozilla.org": "documentation",
    "en.wikipedia.org": "encyclopedia",
    "stackoverflow.com": "qanda", "arxiv.org": "academic",
    "www.university.edu.sa": "university", "www.nasa.gov": "government",
    "www.youtube.com": "media", "openai.com": "corporate",
    "www.coursera.org": "education", "news.ycombinator.com": "news",
    "www.google.com": "search",
}


def load_candidate():
    """Reload the saved candidate and its operating threshold."""
    import joblib

    from app.ml.feature_schema import (
        FEATURE_EXTRACTOR_VERSION,
        assert_schema_matches,
        model_feature_indices,
    )

    if not CANDIDATE.exists():
        return None
    bundle = joblib.load(CANDIDATE)
    assert_schema_matches(bundle["feature_names"], FEATURE_EXTRACTOR_VERSION)
    meta = json.loads(
        (BACKEND / "models" / "basirah-url-v3.metadata.json").read_text(encoding="utf-8")
    )
    return {
        "estimator": bundle["estimator"],
        "columns": model_feature_indices(),
        "threshold": float(meta["selected_threshold"]),
    }


def probability_of(model: dict[str, Any], url: str) -> float:
    from app.services.feature_extractor import extract_features, to_vector
    from app.services.url_analyzer import InvalidURLError, normalize

    try:
        parsed = normalize(url)
    except InvalidURLError:
        return float("nan")
    full = to_vector(extract_features(parsed))
    vector = [full[i] for i in model["columns"]]
    proba = model["estimator"].predict_proba([vector])
    classes = list(getattr(model["estimator"], "classes_", [0, 1]))
    column = classes.index(1) if 1 in classes else len(classes) - 1
    return float(proba[0][column])


# ====================================================================
# 1. CATEGORY-LEVEL FALSE POSITIVE RATE
# ====================================================================


def category_fpr(model: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Real-world legitimate FP rate broken down by site category.

    This is the breakdown that says WHICH kinds of legitimate URL the
    model still gets wrong, which a single aggregate rate cannot show.
    """
    from app.ml.semantic_cases import LEGITIMATE_CASES

    rows: list[dict[str, Any]] = []
    for case in LEGITIMATE_CASES:
        host = case.url.split("://")[-1].split("/")[0].lower()
        category = CATEGORY_BY_HOST.get(host, case.category)
        probability = probability_of(model, case.url) if model else float("nan")
        flagged = bool(model) and probability >= model["threshold"]
        rows.append(
            {
                "category": category,
                "url": case.url,
                "probability": round(probability, 6) if probability == probability else None,
                "flagged": flagged,
                "rationale": case.rationale,
            }
        )

    # Aggregate per category.
    by_category: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = by_category.setdefault(
            row["category"], {"n": 0, "flagged": 0}
        )
        entry["n"] += 1
        entry["flagged"] += int(row["flagged"])

    out: list[dict[str, Any]] = []
    for category, entry in sorted(
        by_category.items(), key=lambda kv: -kv[1]["flagged"]
    ):
        out.append(
            {
                "category": category,
                "n_urls": entry["n"],
                "n_flagged_as_phishing": entry["flagged"],
                "false_positive_rate": round(entry["flagged"] / entry["n"], 4),
                "urls": "|".join(r["url"] for r in rows if r["category"] == category),
            }
        )
    return out


# ====================================================================
# 2. FALSE POSITIVE / FALSE NEGATIVE DETAIL
# ====================================================================


def error_tables(model: dict[str, Any] | None) -> tuple[list, list]:
    """Per-error detail: probability, path structure, triggered rules."""
    from app.ml.semantic_cases import ALL_CASES
    from app.services.heuristic_engine import evaluate

    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []

    for case in ALL_CASES:
        probability = probability_of(model, case.url) if model else float("nan")
        flagged = bool(model) and probability >= model["threshold"]
        predicted = PHISHING if flagged else LEGITIMATE
        if predicted == case.expected_label:
            continue

        try:
            from app.services.url_analyzer import normalize

            parsed = normalize(case.url)
            host = parsed.hostname
            path = parsed.path or ""
            depth = len([s for s in path.split("/") if s])
            query_count = len(parsed.query.split("&")) if parsed.query else 0
            rules = [f.id for f in evaluate(parsed) if f.triggered]
        except Exception:
            host, depth, query_count, rules = "", 0, 0, []

        record = {
            "url": case.url,
            "category": case.category,
            "expected": "phishing" if case.expected_label == PHISHING else "legitimate",
            "probability": round(probability, 6) if probability == probability else None,
            "risk_score": round(probability * 100, 2) if probability == probability else None,
            "threshold": model["threshold"] if model else None,
            "path_depth": depth,
            "query_count": query_count,
            "hostname": host,
            "subdomain_depth": len(host.split(".")) - 2 if host else 0,
            "triggered_heuristics": "|".join(rules) if rules else "none",
        }
        if case.expected_label == LEGITIMATE:
            false_positives.append(record)
        else:
            false_negatives.append(record)

    false_positives.sort(key=lambda r: -(r["probability"] or 0))
    false_negatives.sort(key=lambda r: (r["probability"] or 0))
    return false_positives, false_negatives


# ====================================================================
# 3. PATH-BIAS STUDY
# ====================================================================


def path_bias(model: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Does phishing probability still track path complexity?

    The Phase 2D hypothesis is that augmenting the training distribution
    with path-bearing legitimate URLs REDUCES this dependence. Measuring
    mean predicted probability against path depth, for legitimate and
    phishing rows separately, tests exactly that.
    """
    from app.ml.corpus_adapters import ADAPTERS
    from app.ml.datasets import load_processed
    from app.services.feature_extractor import extract_features, to_vector
    from app.services.url_analyzer import InvalidURLError, normalize

    rows: list[dict[str, Any]] = []
    for name in sorted(ADAPTERS):
        try:
            corpus = load_processed(name)
        except Exception:
            continue
        step = max(len(corpus) // 15000, 1)
        for row in corpus[::step]:
            try:
                parsed = normalize(row.url)
            except InvalidURLError:
                continue
            path = parsed.path or ""
            depth = len([s for s in path.split("/") if s])
            probability = probability_of(model, row.url) if model else float("nan")
            rows.append(
                {
                    "corpus": name,
                    "label": "phishing" if row.label == PHISHING else "legitimate",
                    "path_depth": min(depth, 6),
                    "probability": probability,
                }
            )

    buckets: dict[tuple[str, int], list[float]] = {}
    for row in rows:
        if row["probability"] != row["probability"]:
            continue
        key = (row["label"], row["path_depth"])
        buckets.setdefault(key, []).append(row["probability"])

    out: list[dict[str, Any]] = []
    for label in ("legitimate", "phishing"):
        for depth in range(7):
            values = buckets.get((label, depth))
            if not values or len(values) < 10:
                continue
            out.append(
                {
                    "label": label,
                    "path_depth": depth,
                    "n": len(values),
                    "mean_probability": round(float(np.mean(values)), 6),
                    "median_probability": round(float(np.median(values)), 6),
                }
            )
    return out


def main() -> int:
    log("=" * 66)
    log("Phase 2D — derived analysis artifacts")
    log("=" * 66)

    model = load_candidate()
    if model is None:
        log("no candidate bundle; writing what can be derived without it")
    else:
        log(f"  candidate loaded, threshold {model['threshold']:.6f}")

    # 1. category FPR
    categories = category_fpr(model)
    write_csv(RESULTS / "category_fpr.csv", categories)
    log(f"  category_fpr.csv ({len(categories)} categories)")

    # 2. FP / FN detail
    fps, fns = error_tables(model)
    write_csv(RESULTS / "false_positive_analysis.csv", fps)
    write_csv(RESULTS / "false_negative_analysis.csv", fns)
    log(f"  false_positive_analysis.csv ({len(fps)})")
    log(f"  false_negative_analysis.csv ({len(fns)})")

    # 3. path bias
    bias = path_bias(model)
    write_csv(RESULTS / "path_bias_analysis.csv", bias)
    log(f"  path_bias_analysis.csv ({len(bias)} rows)")

    # The headline the path study answers.
    log("")
    log("  PATH-BIAS SUMMARY (mean predicted phishing probability)")
    log(f"    {'label':12}{'depth':>6}{'n':>8}{'mean p':>10}")
    for row in bias:
        log(
            f"    {row['label']:12}{row['path_depth']:>6}"
            f"{row['n']:>8,}{row['mean_probability']:>10.4f}"
        )

    log("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())