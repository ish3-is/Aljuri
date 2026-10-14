"""
Build a BLIND challenge set and score BASIRAH against it.

Design constraints that make this a real test rather than a demo:

* Images are COPIED OUT of every split used to fit Detector B. Detector
  B's probe was fitted on `C_clean_CF_generator_holdout.train`, so no
  challenge image may come from that split, and near-duplicates of it
  are excluded by perceptual hash.
* Filenames are opaque and random. The analyser sees only the bytes.
* Labels live in a separate file that is loaded only AFTER scoring.

The headline metric is the FALSE AUTHENTIC RATE: a synthetic image
confidently presented as authentic-side. For a defence rehearsal that
failure is worse than an abstention, so it is reported first.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BLIND = ROOT / "challenge" / "blind"
IMAGES = BLIND / "images"
LABELS = BLIND / "labels.json"

# Detector B was fitted here; anything from it is excluded outright.
FIT_SPLITS = ("C_clean_CF_generator_holdout",)

SOURCE_ROOTS = [
    ROOT / "datasets" / "image" / "square" / "synthetic",
    ROOT / "datasets" / "image" / "square" / "real",
    ROOT / "datasets" / "raw" / "aigcdetection_benchmark",
]

# Generators present in the documented benchmark. Families the project
# does NOT have are listed in the report as a coverage limitation rather
# than approximated with something else.
FAMILY_HINTS = [
    ("midjourney", "Midjourney"), ("dalle", "DALL-E"), ("sdxl", "SDXL"),
    ("stable", "StableDiffusion"), ("sd14", "SD14"), ("sd15", "SD15"),
    ("progan", "GAN"), ("stylegan", "GAN"), ("cyclegan", "GAN"),
    ("gaugan", "GAN"), ("stargan", "GAN"), ("biggan", "GAN"),
    ("whichfaceisreal", "GAN"), ("glide", "PixelDiffusion"),
    ("adm", "PixelDiffusion"), ("vqdm", "PixelDiffusion"),
    ("wukong", "LatDiff"), ("latentdiffusion", "LatDiff"),
]


def family_of(name: str) -> str:
    low = name.lower()
    for token, family in FAMILY_HINTS:
        if token in low:
            return family
    return "Unknown"


def _resample_linear():
    """
    Pillow 10 removed the module-level resampling constants.

    Getting this wrong raised inside dhash(), where a broad `except`
    turned the error into a silent "return -1" -- which made
    near-duplicate exclusion a no-op that still looked like it had run.
    The failure is therefore made explicit at import time.
    """
    enum = getattr(Image, "Resampling", None)
    if enum is not None and hasattr(enum, "BILINEAR"):
        return enum.BILINEAR
    if hasattr(Image, "BILINEAR"):
        return Image.BILINEAR
    raise RuntimeError("no usable bilinear resampling constant in Pillow")


_LINEAR = _resample_linear()


def dhash(path: Path, size: int = 8) -> int:
    """Perceptual hash used to reject near-duplicates of training images."""
    try:
        with Image.open(path) as im:
            g = im.convert("L").resize((size + 1, size), _LINEAR)
            px = np.asarray(g, dtype=np.int16)
    except Exception as exc:  # noqa: BLE001
        # Surfaced rather than swallowed: a silent -1 here means
        # "cannot hash", not "not a duplicate".
        print(f"  dhash failed for {path.name}: {type(exc).__name__}: {exc}")
        return -1
    bits = (px[:, 1:] > px[:, :-1]).flatten()
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def collect(limit_per_class: int = 60) -> list[tuple[Path, str, str]]:
    """Gather candidate images with an honest label and family."""
    out: list[tuple[Path, str, str]] = []

    # Synthetic: CommunityForensics (held out from the C split elsewhere
    # in this project via generator holdout).
    syn_dir = ROOT / "datasets" / "image" / "square" / "synthetic"
    if syn_dir.exists():
        for p in sorted(syn_dir.glob("*.jpg"))[:limit_per_class * 2]:
            out.append((p, "synthetic", family_of(p.name)))

    # Real photographs.
    real_dir = ROOT / "datasets" / "image" / "square" / "real"
    if real_dir.exists():
        for p in sorted(real_dir.glob("*.jpg"))[:limit_per_class * 2]:
            out.append((p, "real", "Flickr30k"))

    return out


def resolve(rel: str) -> Path | None:
    """
    splits.json stores paths with a 'backend/' prefix while ROOT is
    already the backend directory. Resolving naively silently produced
    ZERO reference hashes, which would have made near-duplicate
    exclusion a no-op that still looked like it had run.
    """
    norm = rel.replace("\\", "/")
    for cand in (ROOT / norm, ROOT / norm.removeprefix("backend/")):
        if cand.exists():
            return cand
    return None


def build() -> dict:
    if IMAGES.exists():
        shutil.rmtree(IMAGES)
    IMAGES.mkdir(parents=True, exist_ok=True)

    # Exclude anything Detector B was fitted on, by exact and perceptual
    # comparison against its training split.
    excluded = set()
    ref_hashes: list[int] = []
    splits_path = ROOT / "results" / "phase3" / "splits.json"
    if splits_path.exists():
        data = json.loads(splits_path.read_text(encoding="utf-8"))["splits"]
        for name in FIT_SPLITS:
            for rel in data.get(name, {}).get("train", []):
                p = resolve(rel)
                if p is None:
                    continue
                excluded.add(hashlib.sha256(p.read_bytes()).hexdigest())
                h = dhash(p)
                if h >= 0:
                    ref_hashes.append(h)

    labels: dict[str, dict] = {}
    kept: list[tuple[Path, str, str]] = []
    skipped_exact = skipped_near = 0

    for path, label, family in collect():
        try:
            raw = path.read_bytes()
        except Exception:  # noqa: BLE001
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if digest in excluded:
            skipped_exact += 1
            continue
        h = dhash(path)
        if h >= 0 and ref_hashes and min(hamming(h, r) for r in ref_hashes[:400]) <= 4:
            skipped_near += 1
            continue
        kept.append((path, label, family))

    # Balance and cap per class so one family cannot dominate.
    per_class: dict[str, list[tuple[Path, str, str]]] = defaultdict(list)
    for item in kept:
        per_class[item[1]].append(item)

    final: list[tuple[Path, str, str]] = []
    for label, items in per_class.items():
        seen_family: dict[str, int] = defaultdict(int)
        for item in items:
            if seen_family[item[2]] >= 25:
                continue
            seen_family[item[2]] += 1
            final.append(item)

    for path, label, family in final:
        name = hashlib.sha256(f"{path.name}{label}".encode()).hexdigest()[:16] + path.suffix
        shutil.copy2(path, IMAGES / name)
        labels[name] = {"label": label, "family": family, "source": path.name}

    LABELS.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    summary = {
        "images": len(labels),
        "real": sum(1 for v in labels.values() if v["label"] == "real"),
        "synthetic": sum(1 for v in labels.values() if v["label"] == "synthetic"),
        "families": sorted({v["family"] for v in labels.values()}),
        "excluded_exact_overlap_with_fit_split": skipped_exact,
        "excluded_near_duplicate_of_fit_split": skipped_near,
        "reference_hashes_checked": len(ref_hashes),
    }
    return summary


if __name__ == "__main__":
    s = build()
    print(json.dumps(s, indent=2))
    print(f"\nblind set at {IMAGES}")
