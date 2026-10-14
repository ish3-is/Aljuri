"""
Phase 2B — remaining experiment stages.

Kept out of the runner so the orchestration reads as a stage list rather
than a wall of code, and so each stage is independently testable.
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

from app.ml.datasets import PROCESSED_DIR, AuditedRow, sha256_of  # noqa: E402
from app.ml.experiment import (  # noqa: E402
    MetricSet,
    apply_platt,
    compute_metrics,
    fit_isotonic,
    fit_platt_scaler,
    model_file_size_mb,
    timed_probabilities,
)
from app.ml.feature_schema import FEATURE_GROUPS, current_schema  # noqa: E402
from app.ml.model_loader import save_model  # noqa: E402
from app.services.feature_extractor import FEATURE_NAMES  # noqa: E402
from app.services.heuristic_engine import evaluate, heuristic_risk  # noqa: E402
from app.services.risk_engine import fuse  # noqa: E402
from app.services.url_analyzer import InvalidURLError, normalize  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results" / "phase2b"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


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


# ====================================================================
# EXTERNAL DATASET ADAPTER
# ====================================================================

MUD_PHISHING = {"phishing"}
MUD_BENIGN = {"benign"}
MUD_EXCLUDED = {"defacement", "malware"}


def load_external(path: Path) -> tuple[list[AuditedRow], dict[str, Any]]:
    """Load the independent dataset, keeping only comparable classes.

    MUD labels are multi-class: benign / defacement / phishing / malware.
    Only benign and phishing are commensurable with a
    phishing-vs-legitimate task. Defacement and malware are DIFFERENT
    threat classes; folding them into "phishing" would measure the model
    against a target it was never trained for and would understate it for
    reasons unrelated to generalization.

    Results are cached to datasets/processed/ because a full pass over
    632k rows takes ~35s and the raw file never changes.
    """
    csv.field_size_limit(10**9)

    cache = PROCESSED_DIR / "mud2026_clean.csv"
    meta_cache = PROCESSED_DIR / "mud2026_summary.json"

    if cache.exists() and meta_cache.exists():
        rows = _read_rows_csv(cache)
        return rows, json.loads(meta_cache.read_text(encoding="utf-8"))

    phishing_urls: set[str] = set()
    benign_urls: set[str] = set()
    excluded: dict[str, int] = {}
    seen: set[str] = set()
    duplicates = 0
    malformed = 0
    total = 0

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for record in csv.DictReader(handle):
            total += 1
            token = (record.get("class_label") or "").strip().lower()
            url = (record.get("url") or "").strip()
            if not url:
                continue

            if token in MUD_EXCLUDED:
                excluded[token] = excluded.get(token, 0) + 1
                continue
            if token in MUD_PHISHING:
                target = phishing_urls
            elif token in MUD_BENIGN:
                target = benign_urls
            else:
                key = f"unrecognised:{token[:16]}"
                excluded[key] = excluded.get(key, 0) + 1
                continue

            seen.add(url.lower())
            try:
                parsed = normalize(url)
            except InvalidURLError:
                malformed += 1
                continue
            target.add(parsed.normalized.lower())

    # A URL in both classes is contradictory; drop it rather than guess.
    overlap = phishing_urls & benign_urls
    phishing_urls -= overlap
    benign_urls -= overlap

    rows: list[AuditedRow] = []
    for url in sorted(phishing_urls):
        rows.append(_make_row(url, 1, "mud2026"))
    for url in sorted(benign_urls):
        rows.append(_make_row(url, 0, "mud2026"))

    summary = {
        "dataset": "Malicious URL Detection Dataset Enhanced 2026",
        "raw_rows_in_file": total,
        "excluded_by_class": excluded,
        "excluded_reason": (
            "defacement and malware are distinct threat classes; "
            "including them as phishing would test a different target"
        ),
        "conflicting_urls_dropped": len(overlap),
        "duplicates_dropped": duplicates,
        "malformed_dropped": malformed,
        "phishing_rows": len(phishing_urls),
        "benign_rows": len(benign_urls),
        "usable_rows": len(rows),
        "distinct_registered_domains": len({r.registered_domain for r in rows}),
        "overlap_with_training_domains": None,
    }

    _write_rows_csv(cache, rows)
    meta_cache.parent.mkdir(parents=True, exist_ok=True)
    meta_cache.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return rows, summary


def _write_rows_csv(path: Path, rows: list[AuditedRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["url", "normalized", "label", "registered_domain", "scheme", "source"])
        for row in rows:
            writer.writerow(
                [row.url, row.normalized, row.label, row.registered_domain, row.scheme, row.source]
            )


def _read_rows_csv(path: Path) -> list[AuditedRow]:
    out: list[AuditedRow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            out.append(
                AuditedRow(
                    url=record["url"],
                    normalized=record["normalized"],
                    label=int(record["label"]),
                    registered_domain=record["registered_domain"],
                    scheme=record["scheme"],
                    hostname="",
                    uses_https=record["scheme"] == "https",
                    source=record["source"],
                )
            )
    return out


def _make_row(url: str, label: int, source: str) -> AuditedRow:
    parsed = normalize(url)
    return AuditedRow(
        url=url,
        normalized=parsed.normalized,
        label=label,
        registered_domain=parsed.registered_domain or parsed.hostname,
        scheme=parsed.scheme,
        hostname=parsed.hostname,
        uses_https=parsed.uses_https,
        source=source,
    )


# ====================================================================
# HEURISTIC + FUSION FEATURES
# ====================================================================

NO_MODEL_PREDICTION_CACHE: dict[int, Any] = {}


class _NoModel:
    """Stand-in Prediction for the heuristics-only arm of the ablation."""

    available = False
    probability = None
    model_name = "none"
    model_version = "0"
    reason = "ablation: heuristics only"


def heuristic_column(
    rows: list[AuditedRow], indices: np.ndarray | None = None
) -> np.ndarray:
    """Heuristic risk 0-100 for each row, from the PRODUCTION engine."""
    selected = (
        [rows[int(i)] for i in indices]
        if indices is not None
        else rows
    )
    out = np.zeros(len(selected), dtype=np.float32)
    for position, row in enumerate(selected):
        try:
            parsed = normalize(row.url)
        except InvalidURLError:
            continue
        score, _fired = heuristic_risk(evaluate(parsed))
        out[position] = score
    return out


def fuse_risk(
    ml_risk: np.ndarray, heuristic_risk_values: np.ndarray, ml_weight: float
) -> np.ndarray:
    """Weighted fusion of the ML and heuristic risk signals.

    Interpretable by construction: one number, one formula, stated in the
    response the user sees. ml_weight is the share given to the model;
    the remainder goes to the heuristics.
    """
    heuristic_weight = 1.0 - ml_weight
    combined = ml_weight * ml_risk + heuristic_weight * heuristic_risk_values
    return np.clip(combined, 0.0, 100.0)
