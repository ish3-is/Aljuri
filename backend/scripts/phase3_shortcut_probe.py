"""
Shortcut probe: can a model separate real from synthetic WITHOUT looking
at image content?

If it can, the corpus is broken and any ROC-AUC measured on it is
meaningless. This is the image-phase equivalent of the Phase 2C
source-classifier diagnostic, and it runs BEFORE training for exactly
that reason.

Three probes, in increasing order of severity:

1. **Metadata-only probe** - predict class from width, height, format,
   file size and aspect ratio alone. These are free facts about the
   container, requiring no pixels.
2. **Downsampled-pixels probe** - a logistic classifier on a heavily
   blurred 32x32 thumbnail. If this scores highly, the classes differ in
   gross visual statistics (usually resolution or colour processing)
   rather than in synthetic-media artefacts.
3. **Per-source resolution/format table** - the raw evidence.

A probe near chance means the corpus is usable. A probe near perfect
means the corpus must be fixed before any model is trained.
"""

from __future__ import annotations

import glob
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
RAW = BACKEND / "datasets" / "image" / "square"  # square-normalized corpus
OUT = BACKEND / "results" / "phase3" / "shortcut_findings.json"
SEED = 42


def collect() -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    """Label by DIRECTORY, which the acquirer set from source semantics.

    real = flickr30k/real + communityforensics_small/real
    synthetic = communityforensics_small/synthetic
    """
    labelled: list[tuple[Path, int]] = []
    for path in sorted(RAW.rglob("*")):
        if not path.is_file():
            continue
        parts = path.parts
        label: int | None = None
        source = None
        name = path.name
        if name.startswith("flickr30k__"):
            label, source = 0, "flickr30k"
        elif name.startswith("communityforensics__"):
            # Normalized corpus stores class as the parent directory.
            if "synthetic" in parts:
                label, source = 1, "communityforensics"
            elif "real" in parts:
                label, source = 0, "communityforensics"
        elif "real" in parts:
            label, source = 0, "unknown"
        elif "synthetic" in parts:
            label, source = 1, "unknown"
        if label is not None:
            labelled.append((path, label))
    return labelled, []


def container_features(path: Path) -> list[float] | None:
    try:
        with Image.open(path) as image:
            width, height = image.size
            fmt = image.format or "?"
    except Exception:  # noqa: BLE001
        return None
    size_kb = path.stat().st_size / 1024.0
    return [
        float(width),
        float(height),
        float(max(width, height)),
        float(min(width, height)),
        width / max(height, 1),
        float(size_kb),
        1.0 if fmt == "PNG" else 0.0,
        1.0 if fmt == "JPEG" else 0.0,
        1.0 if fmt == "WEBP" else 0.0,
    ]


def thumbnail_features(path: Path) -> np.ndarray | None:
    try:
        with Image.open(path) as image:
            thumb = image.convert("RGB").resize((32, 32), Image.BILINEAR)
            array = np.asarray(thumb, dtype=np.float32) / 255.0
    except Exception:  # noqa: BLE001
        return None
    return array.reshape(-1)


def auc_probe(features: list, labels: list[int], name: str) -> float | None:
    if len(set(labels)) < 2 or len(labels) < 40:
        return None
    X = np.asarray(features, dtype=np.float64)
    y = np.asarray(labels)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=SEED, stratify=y
    )
    if len(set(y_train)) < 2:
        return None
    model = LogisticRegression(max_iter=2000, random_state=SEED)
    model.fit(X_train, y_train)
    score = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"  {name:34} ROC-AUC = {score:.4f}")
    return float(score)


def main() -> int:
    labelled, _ = collect()
    if not labelled:
        print("no labelled images found")
        return 1

    print(f"labelled images: {len(labelled):,}")
    print(f"  real      : {sum(1 for _, y in labelled if y == 0):,}")
    print(f"  synthetic : {sum(1 for _, y in labelled if y == 1):,}")

    # ---- per-source table -------------------------------------------
    print()
    print("=== per-source resolution and format (the raw evidence) ===")
    table: dict[str, dict] = {}
    by_source: dict[tuple[str, int], list[Path]] = {}
    for path, label in labelled:
        source = "flickr30k" if path.name.startswith("flickr30k__") else "communityforensics"
        by_source.setdefault((source, label), []).append(path)

    for (source, label), paths in sorted(by_source.items()):
        random.seed(SEED)
        sample = random.sample(paths, min(300, len(paths)))
        formats: Counter[str] = Counter()
        long_edges: list[int] = []
        for path in sample:
            try:
                with Image.open(path) as image:
                    formats[image.format or "?"] += 1
                    long_edges.append(max(image.size))
            except Exception:  # noqa: BLE001
                continue
        long_edges.sort()
        name = f"{source}/{'real' if label == 0 else 'synthetic'}"
        table[name] = {
            "count": len(paths),
            "formats": dict(formats),
            "long_edge_min": long_edges[0] if long_edges else None,
            "long_edge_median": long_edges[len(long_edges) // 2] if long_edges else None,
            "long_edge_max": long_edges[-1] if long_edges else None,
        }
        median = table[name]["long_edge_median"]
        print(
            f"  {name:34} n={len(paths):<6} "
            f"{str(dict(formats)):28} long-edge median={median}"
        )

    # ---- probes -----------------------------------------------------
    print()
    print("=== shortcut probes (higher = corpus is more separable) ===")
    container, thumbs, labels = [], [], []
    for path, label in labelled:
        c = container_features(path)
        if c is None:
            continue
        t = thumbnail_features(path)
        if t is None:
            continue
        container.append(c)
        thumbs.append(t)
        labels.append(label)

    print(f"  probe sample: {len(labels):,} images")
    container_auc = auc_probe(container, labels, "container-only (w/h/format/size)")
    thumb_auc = auc_probe(thumbs, labels, "32x32 thumbnail pixels")

    # ---- verdict ----------------------------------------------------
    print()
    verdict = "SHORTCUT CONTROLLED"
    detail = "neither probe approaches a perfect score"
    if container_auc is not None and container_auc > 0.90:
        verdict = "SHORTCUT PRESENT - BLOCKING"
        detail = (
            f"Container metadata alone reaches ROC-AUC {container_auc:.4f}. The classes "
            "differ in resolution or file format, not (only) in synthetic-media "
            "characteristics. Any model trained on this corpus would learn dataset "
            "provenance. Fix the corpus before training."
        )
    elif thumb_auc is not None and thumb_auc > 0.95:
        verdict = "SHORTCUT SUSPECTED - BLOCKING"
        detail = (
            f"Even a 32x32 thumbnail reaches ROC-AUC {thumb_auc:.4f}, indicating gross "
            "visual statistics separate the classes."
        )

    print(f"VERDICT: {verdict}")
    if detail:
        print(f"  {detail}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            existing = {}
    existing["shortcut_probe"] = {
        "verdict": verdict,
        "detail": detail,
        "container_only_roc_auc": container_auc,
        "thumbnail_32px_roc_auc": thumb_auc,
        "per_source": table,
        "total_images": len(labels),
        "seed": SEED,
    }
    OUT.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())