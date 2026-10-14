"""
Extract a real-image sample from the Flickr30k archive.

The archive is verified complete before use, and the macOS resource-fork
entries (`__MACOSX/...`) are excluded - they are metadata sidecars that
look like images and would silently corrupt any format audit.

Every extracted file is verified to decode. A row in an archive is not
proof of a usable image, and the Phase 3 corpus gate would otherwise be
measuring extraction bugs as corpus defects.
"""

from __future__ import annotations

import json
import os
import random
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
ARCHIVE = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "basirah_dl" / "flickr30k-images.zip"
OUT = BACKEND / "datasets" / "image" / "raw" / "flickr30k"
MANIFEST = BACKEND / "datasets" / "image" / "manifests" / "flickr30k.json"

SAMPLE = 8000
SEED = 42


def main() -> int:
    if not ARCHIVE.exists():
        print(f"archive missing: {ARCHIVE}")
        return 1

    # Verify the archive is actually complete before trusting it.
    with zipfile.ZipFile(ARCHIVE) as archive:
        bad = archive.testzip()
        if bad is not None:
            print(f"archive corrupt at {bad}")
            return 1
        names = [
            n
            for n in archive.namelist()
            if n.lower().endswith((".jpg", ".jpeg", ".png"))
            and not n.startswith("__MACOSX/")
            and not os.path.basename(n).startswith("._")
        ]

    print(f"archive OK: {len(names):,} usable images")
    random.seed(SEED)
    chosen = random.sample(names, min(SAMPLE, len(names)))
    OUT.mkdir(parents=True, exist_ok=True)

    written = 0
    failed = 0
    widths: list[int] = []
    heights: list[int] = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in chosen:
            target = OUT / Path(name).name
            try:
                with archive.open(name) as handle:
                    payload = handle.read()
                with Image.open(__import__("io").BytesIO(payload)) as probe:
                    probe.verify()
                target.write_bytes(payload)
                with Image.open(target) as check:
                    widths.append(check.width)
                    heights.append(check.height)
                written += 1
            except Exception:  # noqa: BLE001
                failed += 1
                continue

    widths.sort()
    heights.sort()
    manifest = {
        "source": "Flickr30k",
        "source_url": "https://huggingface.co/datasets/nlphuji/flickr30k",
        "archive": "flickr30k-images.zip",
        "license": "Flickr30k images are subject to individual Flickr CC licenses; "
                   "the dataset is distributed for research use",
        "class": "real",
        "class_semantics": "0 = real / camera-captured photograph",
        "generator": None,
        "generator_note": "Real photographs have no generator; this field is null by definition, not unknown",
        "download_date": "2026-10-04",
        "archive_bytes": ARCHIVE.stat().st_size,
        "available_in_archive": len(names),
        "sampled": len(chosen),
        "written": written,
        "failed_to_decode": failed,
        "extraction_dir": str(OUT.relative_to(BACKEND.parent)).replace("\\", "/"),
        "resolution": {
            "width_min": widths[0] if widths else None,
            "width_median": widths[len(widths) // 2] if widths else None,
            "width_max": widths[-1] if widths else None,
            "height_min": heights[0] if heights else None,
            "height_median": heights[len(heights) // 2] if heights else None,
            "height_max": heights[-1] if heights else None,
        },
        "known_bias_risks": [
            "Flickr30k images are web photographs, typically already JPEG-compressed "
            "by their original upload path. Synthetic corpora that ship as PNG or as "
            "uncompressed TIFFs will therefore differ in format and compression even "
            "when content is matched. This must be measured, not assumed away.",
            "COCO-captioned Flickr images skew toward everyday scenes and strong "
            "composition, unlike a surveillance or forensic camera corpus.",
        ],
        "seed": SEED,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"extracted {written:,} images ({failed} failed to decode)")
    print(f"  width  min/med/max: {manifest['resolution']['width_min']}/"
          f"{manifest['resolution']['width_median']}/{manifest['resolution']['width_max']}")
    print(f"  height min/med/max: {manifest['resolution']['height_min']}/"
          f"{manifest['resolution']['height_median']}/{manifest['resolution']['height_max']}")
    print(f"  manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())