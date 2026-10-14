"""
Neutralise the corpus shortcut.

The probe measured container metadata alone at ROC-AUC 0.9999 - a model
reading only width, height, format and file size would separate the
classes almost perfectly while learning nothing about synthetic media.

The fix is to remove the shortcut's *availability*, not to hope a model
ignores it. Every image is re-encoded into a single common container at a
single common resolution:

* all output is JPEG at a fixed long edge (default 256px)
* all output is re-compressed at one fixed quality (default 90)

Decisions and their reasons:

**Resize DOWN, never up.** Synthetics arrive at 512-1024px and Flickr
reals at 500px. Downscaling both to a common long edge removes the
resolution cue. Upsampling instead would resample one class and not the
other, creating a resampling halo that is itself a class marker.

**One container, one quality.** Mixed PNG/JPEG is a perfect class label
here. A single format at a single quality removes both the format cue and
the compression-quality cue.

**256px rather than 512.** Small enough that upsampling is never needed
for the majority of inputs, which avoids introducing resampling artifacts
at all.

**JPEG rather than PNG.** PNG is lossless, so it would preserve the
compression-history differences between sources instead of flattening
them. Re-encoding both classes through the same lossy path equalises
compression history as well as format.

After this runs, the probe is re-run and must fall well below the 0.90
blocking threshold before any model training is allowed.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
RAW = BACKEND / "datasets" / "image" / "raw"
OUT = BACKEND / "datasets" / "image" / "normalized"
REPORT = BACKEND / "results" / "phase3" / "normalization.json"

LONG_EDGE = 256
JPEG_QUALITY = 90
SEED = 42


def label_for(path: Path) -> int | None:
    parts = path.parts
    if "synthetic" in parts:
        return 1
    if "real" in parts:
        return 0
    return None


def resize_long_edge(image: Image.Image, target: int) -> Image.Image:
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("no pixels")
    if width >= height:
        new = (target, max(1, round(height * target / width)))
    else:
        new = (max(1, round(width * target / height)), target)
    return image.resize(new, Image.BILINEAR)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = sorted(p for p in RAW.rglob("*") if p.is_file())

    stats = {
        "long_edge": LONG_EDGE,
        "jpeg_quality": JPEG_QUALITY,
        "format": "JPEG",
        "seed": SEED,
        "written": 0,
        "failed": 0,
        "upsampled": 0,
        "per_source": {},
    }

    for label_dir in ("real", "synthetic"):
        (OUT / label_dir).mkdir(parents=True, exist_ok=True)

    random.seed(SEED)
    per_source: Counter[str] = Counter()
    long_edges: list[int] = []

    for path in sources:
        label = label_for(path)
        if label is None:
            continue
        source = "flickr30k" if "flickr30k" in path.parts else "communityforensics"
        try:
            with Image.open(path) as opened:
                image = opened.convert("RGB")
                original_long = max(opened.size)
                if original_long < LONG_EDGE:
                    # Upsampling would create a class-specific resampling
                    # artifact, so it is counted and reported rather than
                    # silently applied to one class.
                    stats["upsampled"] += 1
                resized = resize_long_edge(image, LONG_EDGE)
                target = OUT / ("synthetic" if label else "real") / f"{source}__{path.name}.jpg"
                resized.save(target, format="JPEG", quality=JPEG_QUALITY, optimize=False)
                stats["written"] += 1
                per_source[f"{source}/{'synthetic' if label else 'real'}"] += 1
                long_edges.append(max(resized.size))
        except Exception:  # noqa: BLE001
            stats["failed"] += 1
            continue

    long_edges.sort()
    stats["per_source"] = dict(per_source)
    stats["normalised_long_edge_min"] = long_edges[0] if long_edges else None
    stats["normalised_long_edge_median"] = long_edges[len(long_edges) // 2] if long_edges else None
    stats["normalised_long_edge_max"] = long_edges[-1] if long_edges else None
    stats["output_dir"] = str(OUT.relative_to(BACKEND.parent)).replace("\\", "/")
    stats["rationale"] = (
        "Mixed PNG/JPEG with a 500px-vs-1024px resolution split let a "
        "container-only classifier reach 0.9999 ROC-AUC. Re-encoding every "
        "image to one format at one resolution and one quality removes the "
        "cue rather than relying on a model to ignore it."
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"normalised {stats['written']:,} images ({stats['failed']} failed)")
    print(f"  upsampled inputs: {stats['upsampled']:,} (reported, not hidden)")
    print(f"  per source: {stats['per_source']}")
    print(f"  long edge min/med/max: {stats['normalised_long_edge_min']}/"
          f"{stats['normalised_long_edge_median']}/{stats['normalised_long_edge_max']}")
    print(f"  report: {REPORT}")
    print()
    print("Re-run scripts/phase3_shortcut_probe.py against the normalized")
    print("corpus; the container probe must fall well below 0.90.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())