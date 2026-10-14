"""
Evaluate a trained model and print a report suitable for the
graduation document.

Usage (from the backend directory):

    .venv\\Scripts\\python.exe -m scripts.evaluate_url_model

Reports the persisted metrics from the training run. It does NOT
recompute them from the test set, because the test fold no longer exists
once training has finished — re-deriving numbers at evaluation time is
how reported results quietly drift from what was actually measured.

If no trained model exists, it says so and exits non-zero rather than
printing placeholder numbers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.model_loader import model_path, model_status  # noqa: E402
from app.services.feature_extractor import FEATURE_NAMES  # noqa: E402


def main() -> int:
    status = model_status()

    if not status.available:
        print("No trained model found.")
        print(f"Expected at: {model_path().name}")
        print()
        print("Real model evaluation is pending dataset acquisition.")
        print()
        print("To train one, supply a labelled CSV:")
        print("  .venv\\Scripts\\python.exe -m scripts.train_url_model --data <file.csv>")
        return 1

    meta = status.metadata or {}
    print("=" * 62)
    print("BASIRAH — URL model evaluation report")
    print("=" * 62)
    print(f"Model:        {meta.get('model_name', 'unknown')}")
    print(f"Version:      {meta.get('model_version', 'unknown')}")
    print(f"Trained at:   {meta.get('trained_at', 'unknown')}")
    print(f"Dataset rows: {meta.get('dataset_rows', 'unknown')}")
    print(f"Features:     {meta.get('feature_count', len(FEATURE_NAMES))}")
    print(f"Selection:    {meta.get('selection_rule', 'unknown')}")

    split = meta.get("train_test_split", {})
    if split:
        print(
            f"Split:        {int((1 - split.get('test_size', 0)) * 100)}/"
            f"{int(split.get('test_size', 0) * 100)} stratified, "
            f"random_state={split.get('random_state')}"
        )

    if meta.get("WARNING"):
        print()
        print(f"!! {meta['WARNING']}")

    metrics = meta.get("metrics") or {}
    print()
    print("-" * 62)
    print("Metrics")
    print("-" * 62)
    if not metrics:
        print("  No metrics recorded.")
    else:
        for key in (
            "accuracy",
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "false_positive_rate",
            "false_negative_rate",
        ):
            if key in metrics:
                print(f"  {key:22} {metrics[key]:.4f}")

    all_metrics = meta.get("all_model_metrics") or {}
    if len(all_metrics) > 1:
        print()
        print("-" * 62)
        print("Baseline comparison")
        print("-" * 62)
        header = f"  {'model':22} {'acc':>8} {'prec':>8} {'rec':>8} {'f1':>8} {'auc':>8}"
        print(header)
        for name, m in sorted(
            all_metrics.items(), key=lambda kv: kv[1].get("f1", 0), reverse=True
        ):
            print(
                f"  {name:22} {m.get('accuracy', 0):8.4f} "
                f"{m.get('precision', 0):8.4f} {m.get('recall', 0):8.4f} "
                f"{m.get('f1', 0):8.4f} {m.get('roc_auc', 0):8.4f}"
            )

    print()
    print("Raw metadata:")
    print(json.dumps(meta, indent=2)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
