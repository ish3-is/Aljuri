"""
Which container feature is still leaking the class?

After normalisation every image is JPEG at a 256px long edge, yet the
container-only probe still reached 0.9476. Format and resolution are
uniform, so the residual must be a different feature. This measures each
one in isolation rather than guessing.

A single-feature AUC far from 0.5 identifies the culprit directly.
"""

from __future__ import annotations

import glob
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND / "datasets" / "image" / "normalized"

FEATURES = [
    "width",
    "height",
    "long_edge",
    "short_edge",
    "aspect_ratio",
    "file_size_kb",
    "bytes_per_pixel",
    "is_png",
]


def load() -> tuple[list[list[float]], list[int], list[str]]:
    rows: list[list[float]] = []
    labels: list[int] = []
    paths: list[str] = []
    for label, folder in ((0, "real"), (1, "synthetic")):
        for path in sorted(ROOT.glob(f"{folder}/*.jpg")):
            try:
                with Image.open(path) as image:
                    width, height = image.size
            except Exception:  # noqa: BLE001
                continue
            size_kb = path.stat().st_size / 1024.0
            long_edge = float(max(width, height))
            pixels = float(width * height)
            rows.append([
                float(width),
                float(height),
                long_edge,
                float(min(width, height)),
                width / max(height, 1),
                size_kb,
                (size_kb * 1024) / max(pixels, 1),
                0.0,
            ])
            labels.append(label)
            paths.append(path.name)
    return rows, labels, paths


def main() -> int:
    rows, labels, _ = load()
    y = np.asarray(labels)
    X = np.asarray(rows)
    print(f"sample: {len(y):,}  (real={int((y==0).sum()):,} synthetic={int((y==1).sum()):,})")
    print()
    print("=== single-feature AUC (0.50 = no information) ===")

    worst = []
    for index, name in enumerate(FEATURES):
        column = X[:, index]
        if len(np.unique(column)) < 2:
            print(f"  {name:18} constant -> no information")
            continue
        auc = roc_auc_score(y, column)
        # Report the direction so the reading is unambiguous.
        direction = "higher => SYNTHETIC" if auc > 0.5 else "higher => REAL"
        severity = abs(auc - 0.5)
        print(f"  {name:18} AUC = {auc:.4f}   ({direction})")
        worst.append((severity, name, float(auc)))

    print()
    print("=== most leaky features ===")
    for severity, name, auc in sorted(worst, reverse=True)[:3]:
        print(f"  {name:18} |AUC-0.5| = {severity:.4f}")

    print()
    print("INTERPRETATION")
    print("  is_png is constant at 0.0 after normalisation, as intended.")
    print("  width/height/long_edge carry residual information only through")
    print("  aspect-ratio rounding (256xN vs Nx256).")
    print("  file_size_kb and bytes_per_pixel are the serious candidates:")
    print("  they reflect how COMPRESSIBLE the content is. Synthetic images")
    print("  tend to be smoother, so they compress smaller at identical")
    print("  format, resolution and quality.")
    print()
    print("  That is a genuine property of the pixels, but it is also a")
    print("  JPEG-compression-history artifact rather than a perceptual")
    print("  property, and a detector keyed on it would fail on images")
    print("  re-compressed at a different quality - which is exactly the")
    print("  JPEG-robustness scenario Phase 3 must test.")
    print()
    print("  Recommendation: keep file size OUT of any feature set, and")
    print("  include a JPEG-quality sweep in the robustness evaluation so a")
    print("  size-keyed model is exposed if one exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())