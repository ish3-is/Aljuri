"""Regenerate model_selection.json from the saved artefacts.

The experiment run writes every metric CSV and the model bundle; this
script assembles the selection report from them without retraining, so
the summary can be rebuilt cheaply.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RESULTS = BACKEND / "results" / "phase2b"
MODELS = BACKEND / "models"


def read_csv(name: str) -> list[dict[str, str]]:
    path = RESULTS / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    metadata_path = MODELS / "basirah-url-v1.metadata.json"
    if not metadata_path.exists():
        print("No production model metadata found.")
        return 1

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    comparison = read_csv("model_comparison.csv")
    external = read_csv("external_validation_metrics.csv")
    split_summary = json.loads(
        (RESULTS / "split_summary.json").read_text(encoding="utf-8")
    )
    dataset_summary = json.loads(
        (RESULTS / "dataset_summary.json").read_text(encoding="utf-8")
    )

    selected = metadata["selected_algorithm"]
    grouped = next(
        r for r in comparison
        if r["model"] == selected and r["split_strategy"] == "grouped_domain"
    )
    random_row = next(
        r for r in comparison
        if r["model"] == selected and r["split_strategy"] == "random"
    )

    external_rows: list[dict[str, object]] = []
    for row in external:
        external_rows.append(
            {
                "dataset": row["dataset"],
                "n": int(row["n"]),
                "accuracy": float(row["accuracy"]),
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "f1": float(row["f1"]),
                "roc_auc": float(row["roc_auc"]),
                "fpr": float(row["fpr"]),
                "fnr": float(row["fnr"]),
                "threshold": float(row["threshold"]),
                "shared_registered_domains_with_training": int(
                    row["shared_registered_domains_with_training"]
                ),
            }
        )

    report = {
        "selected_model": selected,
        "production_model_name": metadata["model_name"],
        "rationale": metadata["selection_rationale"],
        "grouped_domain_metrics": grouped,
        "random_split_metrics": random_row,
        "accuracy_delta_random_minus_grouped": round(
            float(random_row["accuracy"]) - float(grouped["accuracy"]), 6
        ),
        "leakage_proof": split_summary["leakage_proof"],
        "split_summary": split_summary["splits"],
        "external_validation": external_rows,
        "dataset": dataset_summary["phiusil"],
        "external_dataset": dataset_summary["external"],
        "thresholds": read_csv("threshold_selection.csv"),
        "model_checksum": metadata.get("model_sha256"),
        "model_size_mb": metadata.get("model_size_mb"),
        "feature_extractor_version": metadata["feature_extractor_version"],
        "selected_threshold": metadata["selected_threshold"],
    }

    out = RESULTS / "model_selection.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"written: {out}")
    print(f"selected model: {selected} ({metadata['model_name']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
