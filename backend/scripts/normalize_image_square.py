"""
Normalize the image corpus to remove class-correlated container cues.

Round 1 (long edge to 256, single JPEG format, single quality) dropped
the container-only probe from 0.9999 to 0.9476 - better, but still
blocking. Round 2 found why: the shortcut was NOT file size, it was
ASPECT RATIO.

    short_edge     AUC 0.9341   (higher => synthetic)
    aspect_ratio   AUC 0.3204   (higher => real)

AI generators emit square images; the Flickr real corpus is predominantly
4:3 landscape. After a long-edge resize, a square image is 256x256 while
a 4:3 photograph is 256x192, so the short edge alone nearly separates the
classes.

This pass forces every image to an exact 256x256 SQUARE, which removes
aspect ratio as a measurable container property entirely.

Crop or pad?
------------
**Crop.** Centre-crop to square discards some content, but padding
invents image area that does not exist in the source, and a synthetic
border is itself an artifact a model could learn. Cropping is the lesser
evil, and the discarded margin is recorded per class so the cost is
visible rather than silent.

Aspect-ratio statistics per class are written to the report so the size of
the content loss is auditable.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
RAW = BACKEND / "datasets" / "image" / "raw"
OUT = BACKEND / "datasets" / "image" / "square"
REPORT = BACKEND / "results" / "phase3" / "normalization_square.json"

SIZE = 256
JPEG_QUALITY = 90


def to_square(image: Image.Image, size: int = SIZE) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side)).resize(
        (size, size), Image.BILINEAR
    )


def label_for(path: Path) -> int | None:
    parts = path.parts
    if "synthetic" in parts:
        return 1
    if "real" in parts:
        return 0
    return None


def main() -> int:
    for folder in ("real", "synthetic"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)

    stats = {
        "size": SIZE,
        "shape": "exact square",
        "jpeg_quality": JPEG_QUALITY,
        "written": 0,
        "failed": 0,
        "cropped_fraction_discarded": {},
        "per_source": Counter(),
        "rationale": (
            "Round-1 normalization unified format and long edge but left "
            "aspect ratio as a near-perfect class marker (short_edge AUC "
            "0.9341), because generators emit square images while the real "
            "corpus is 4:3. Centre-cropping to an exact square removes it. "
            "Padding was rejected: invented image area is itself an artifact."
        ),
    }

    discarded: dict[str, list[float]] = {"real": [], "synthetic": []}

    for path in sorted(p for p in RAW.rglob("*") if p.is_file()):
        label = label_for(path)
        if label is None:
            continue
        source = "flickr30k" if "flickr30k" in path.parts else "communityforensics"
        try:
            with Image.open(path) as opened:
                image = opened.convert("RGB")
                width, height = image.size
                square = to_square(image)
                target = OUT / ("synthetic" if label else "real") / f"{source}__{path.name}.jpg"
                square.save(target, format="JPEG", quality=JPEG_QUALITY)
                stats["written"] += 1
                stats["per_source"][f"{source}/{'synthetic' if label else 'real'}"] += 1
                discarded["synthetic" if label else "real"].append(
                    1.0 - (min(width, height) ** 2) / max(width * height, 1)
                )
        except Exception:  # noqa: BLE001
            stats["failed"] += 1
            continue

    for label, values in discarded.items():
        if values:
            values.sort()
            stats["cropped_fraction_discarded"][label] = {
                "median": round(values[len(values) // 2], 4),
                "max": round(values[-1], 4),
                "mean": round(sum(values) / len(values), 4),
            }

    stats["per_source"] = dict(stats["per_source"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"normalised {stats['written']:,} images to exact {SIZE}x{SIZE} ({stats['failed']} failed)")
    print(f"  per source: {stats['per_source']}")
    print(f"  fraction of area discarded by centre-crop:")
    for label, values in stats["cropped_fraction_discarded"].items():
        print(f"    {label:10} median={values['median']:.1%} mean={values['mean']:.1%} max={values['max']:.1%}")
    print(f"  report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())