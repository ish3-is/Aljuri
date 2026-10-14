"""
Normalize the cross-family corpus and prove the shortcut is gone.

The AIGC-Detection-Benchmark carries an obvious shortcut: synthetic
images are predominantly 256x256 PNG, real images are variable-resolution
JPEG. A detector handed this raw would learn "small PNG = fake" and score
well while detecting nothing.

So the shortcut is measured BEFORE normalization, the corpus is
normalized with a class-symmetric policy, and the probe is repeated
AFTER. No visual model is evaluated until the post-normalization probe
is acceptably low.

Policy
------
**Letterbox (aspect-ratio-preserving pad), not centre-crop.** The first
corpus needed centre-cropping and it cost real images a median 28.6% of
their area while synthetic lost none - an asymmetry we then had to spend
two extra normalization passes cleaning up. Letterboxing keeps every
pixel of both classes and discards nothing.

**Single container, single quality.** Everything becomes JPEG at one
quality so neither the format nor the compression level can encode the
label.

Midjourney is kept in Unknown_Architecture throughout. Its architecture
has never been publicly disclosed and inferring one would be fabrication.
"""

from __future__ import annotations

import csv
import io
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

BACKEND = Path(__file__).resolve().parents[1]
RAW = BACKEND / "datasets" / "image" / "raw" / "aigcdetection_benchmark"
OUT = BACKEND / "datasets" / "image" / "crossfamily"
RESULTS = BACKEND / "results" / "phase3"

SIZE = 256
JPEG_QUALITY = 90
SEED = 42
BLOCKING_THRESHOLD = 0.85


def label_of(path: Path) -> int:
    return 0 if "real" in path.parts else 1


def family_of(path: Path) -> str:
    for part in path.parts:
        if part in {"GAN", "LatDiff", "PixelDiffusion", "Unknown_Architecture"}:
            return part
    return "real"


def generator_of(path: Path) -> str:
    """Generator from the FILENAME is NOT used for labels.

    Filenames do encode the generator (e.g. 000003_Midjourney.png), but
    this is recorded only for reporting a breakdown, never as a training
    or evaluation label. The directory tree and the source manifest are
    the authority; filenames are cross-checked against them.
    """
    stem = path.stem
    if "_" in stem:
        return stem.split("_", 1)[1]
    return "unknown"


def letterbox(image: Image.Image, size: int = SIZE) -> Image.Image:
    """Resize preserving aspect ratio, then pad with edge-sampled colour."""
    width, height = image.size
    scale = size / max(width, height)
    new = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = image.resize(new, Image.BILINEAR)
    if new == (size, size):
        return resized
    samples = [
        resized.getpixel((new[0] // 2, 0)),
        resized.getpixel((new[0] // 2, new[1] - 1)),
        resized.getpixel((0, new[1] // 2)),
        resized.getpixel((new[0] - 1, new[1] // 2)),
    ]
    fill = tuple(sum(c) // len(samples) for c in zip(*samples))
    canvas = Image.new("RGB", (size, size), fill)
    canvas.paste(resized, ((size - new[0]) // 2, (size - new[1]) // 2))
    return canvas


def container_features(path: Path) -> list[float] | None:
    try:
        with Image.open(path) as image:
            width, height = image.size
            fmt = image.format or "?"
    except Exception:  # noqa: BLE001
        return None
    size_bytes = path.stat().st_size
    pixels = max(width * height, 1)
    return [
        float(width), float(height), float(max(width, height)),
        float(min(width, height)), width / max(height, 1),
        size_bytes / 1024.0, size_bytes / pixels,
        1.0 if fmt == "PNG" else 0.0,
        1.0 if fmt == "JPEG" else 0.0,
    ]


NAMES = ["width", "height", "long_edge", "short_edge", "aspect_ratio",
         "file_size_kb", "bytes_per_pixel", "is_png", "is_jpeg"]


def probe(paths: list[Path], labels: list[int], tag: str) -> float | None:
    rows, keep = [], []
    for path, label in zip(paths, labels):
        feature = container_features(path)
        if feature:
            rows.append(feature)
            keep.append(label)
    if len(set(keep)) < 2 or len(rows) < 60:
        return None
    X = np.asarray(rows)
    y = np.asarray(keep)
    if np.allclose(X.std(axis=0), 0):
        return None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=SEED, stratify=y)
    model = LogisticRegression(max_iter=3000, random_state=SEED)
    model.fit(X_train, y_train)
    auc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
    print(f"  {tag:44} AUC = {auc:.4f}")
    return auc


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    raw_paths = sorted(p for p in RAW.rglob("*") if p.is_file())
    labels = [label_of(p) for p in raw_paths]
    print(f"raw corpus: {len(raw_paths):,} images "
          f"(real={labels.count(0):,} synthetic={labels.count(1):,})")
    print(f"  families: {dict(Counter(family_of(p) for p in raw_paths))}")

    # ---- BEFORE ----------------------------------------------------
    print()
    print("=== shortcut probe BEFORE normalization ===")
    before = probe(raw_paths, labels, "container (w/h/format/size)")

    # ---- normalize --------------------------------------------------
    print()
    print(f"=== normalizing: letterbox to {SIZE}x{SIZE} JPEG q{JPEG_QUALITY} ===")
    for folder in ("real", "synthetic"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)

    index_rows = []
    written = failed = 0
    for path in raw_paths:
        label = label_of(path)
        family = family_of(path)
        generator = generator_of(path) if label == 1 else "real"
        target_dir = OUT / ("synthetic" if label else "real") / family
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{path.stem}.jpg"
        try:
            with Image.open(path) as opened:
                square = letterbox(opened.convert("RGB"))
                square.save(target, format="JPEG", quality=JPEG_QUALITY)
            written += 1
            index_rows.append({
                "path": str(target.relative_to(BACKEND.parent)).replace("\\", "/"),
                "label": label,
                "family": family,
                "generator": generator,
            })
        except Exception:  # noqa: BLE001
            failed += 1
            continue

    print(f"  normalized {written:,} images ({failed} failed)")
    print(f"  output: {OUT.relative_to(BACKEND.parent)}")

    # ---- AFTER -----------------------------------------------------
    print()
    print("=== shortcut probe AFTER normalization ===")
    norm_paths = [BACKEND.parent / r["path"] for r in index_rows]
    norm_labels = [r["label"] for r in index_rows]
    after = probe(norm_paths, norm_labels, "container (w/h/format/size)")

    # ---- persist ----------------------------------------------------
    with (RESULTS / "crossfamily_index.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "label", "family", "generator"])
        writer.writeheader()
        writer.writerows(index_rows)

    with (RESULTS / "crossfamily_shortcut_probe.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stage", "roc_auc", "blocking_threshold", "verdict"])
        writer.writerow(["before_normalization", before, BLOCKING_THRESHOLD,
                         "BLOCKED - synthetic is small PNG, real is variable JPEG"])
        writer.writerow(["after_normalization", after, BLOCKING_THRESHOLD,
                         "OK" if after is not None and after < BLOCKING_THRESHOLD
                         else "STILL BLOCKING"])

    (RESULTS / "crossfamily_normalization.json").write_text(json.dumps({
        "policy": "letterbox (aspect-ratio preserving) + single JPEG container at one quality",
        "size": SIZE,
        "jpeg_quality": JPEG_QUALITY,
        "written": written,
        "failed": failed,
        "shortcut_auc_before": before,
        "shortcut_auc_after": after,
        "blocking_threshold": BLOCKING_THRESHOLD,
        "class_symmetric": True,
        "note": ("Midjourney remains labelled Unknown_Architecture. Its "
                 "architecture has never been publicly disclosed and inferring "
                 "one would be fabrication."),
    }, indent=2), encoding="utf-8")

    print()
    print(f"written: {RESULTS / 'crossfamily_shortcut_probe.csv'}")
    print(f"written: {RESULTS / 'crossfamily_index.csv'}")
    if after is not None and after < BLOCKING_THRESHOLD:
        print(f"\nVERDICT: shortcut reduced {before:.4f} -> {after:.4f}. "
              f"Cross-family evaluation may proceed.")
    else:
        print(f"\nVERDICT: shortcut still {after}. Do NOT evaluate visual models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())