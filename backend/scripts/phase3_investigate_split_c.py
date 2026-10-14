"""
Try to DISPROVE the Split C result.

Model A reported ROC-AUC 0.9988 on 109 unseen generators. That is higher
than its random-split score, which is the wrong direction: a detector
meeting a genuinely new generator normally LOSES accuracy, because it is
being asked a harder question. A result that goes UP under a harder test
means the test is not actually harder, or something other than image
content is driving it.

Six independent probes, each able to falsify the number on its own:

  P1  non-pixel classifier   - can width/height/format/size/crop-loss
                               alone separate the classes? No pixels used.
  P2  source-only classifier - can dataset identity alone separate them?
  P3  per-split container probe - is Split C more separable than A and B?
  P4  label permutation      - shuffled labels must give ~0.5. Anything
                               else means leakage in the pipeline.
  P5  matched-source subset  - restrict to real and synthetic that share
                               format, resolution bin and aspect-ratio
                               bin, removing every container cue.
  P6  crop-asymmetry probe   - does "fraction of area discarded by
                               centre-crop" predict the label?

If any probe is high, the 0.9988 is an artifact.
"""

from __future__ import annotations

import csv
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
PROJECT = BACKEND.parent
RESULTS = BACKEND / "results" / "phase3"
SPLITS = RESULTS / "splits.json"
SEED = 42


def label_of(relative: str) -> int:
    return 1 if "/synthetic/" in relative.replace("\\", "/") else 0


def container_row(relative: str) -> dict | None:
    """Everything about the file EXCEPT its pixels."""
    path = PROJECT / relative
    try:
        with Image.open(path) as image:
            width, height = image.size
            fmt = image.format or "?"
    except Exception:  # noqa: BLE001
        return None
    size_bytes = path.stat().st_size
    pixels = max(width * height, 1)
    long_edge = max(width, height)
    short_edge = min(width, height)
    # Crop loss is what normalisation discarded to reach a square.
    crop_loss = 1.0 - (short_edge**2) / pixels if width != height else 0.0
    return {
        "path": relative,
        "label": label_of(relative),
        "source": "flickr30k" if "flickr30k" in relative else "communityforensics",
        "format": fmt,
        "width": width,
        "height": height,
        "long_edge": long_edge,
        "short_edge": short_edge,
        "aspect_ratio": width / max(height, 1),
        "size_bytes": size_bytes,
        "bytes_per_pixel": size_bytes / pixels,
        "crop_loss": crop_loss,
        "source_flickr": 1.0 if "flickr30k" in relative else 0.0,
    }


def auc_of(rows: list[dict], feature_names: list[str], name: str) -> float | None:
    usable = [r for r in rows if r is not None]
    labels = np.asarray([r["label"] for r in usable])
    if len(set(labels.tolist())) < 2 or len(usable) < 60:
        return None
    X = np.asarray([[float(r[f]) for f in feature_names] for r in usable])
    if np.allclose(X.std(axis=0), 0):
        return None
    X_train, X_test, y_train, y_test = train_test_split(
        X, labels, test_size=0.3, random_state=SEED, stratify=labels
    )
    if len(set(y_train.tolist())) < 2:
        return None
    model = LogisticRegression(max_iter=3000, random_state=SEED)
    model.fit(X_train, y_train)
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"    {name:42} AUC = {auc:.4f}")
    return float(auc)


def main() -> int:
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))["splits"]
    findings: dict = {}

    # ---------- distributions per split ---------------------------
    print("=== P0: class x source contingency, per split ===")
    for name, split in splits.items():
        rows = [container_row(p) for p in split["test"]]
        rows = [r for r in rows if r]
        table = Counter((r["label"], r["source"]) for r in rows)
        print(f"  {name}")
        print(f"    real/flickr={table[(0, 'flickr30k')]}  real/cf={table[(0, 'communityforensics')]}"
              f"  syn/flickr={table[(1, 'flickr30k')]}  syn/cf={table[(1, 'communityforensics')]}")
        findings.setdefault("contingency", {})[name] = {
            f"label_{k[0]}_{k[1]}": v for k, v in table.items()
        }

    split_c_test = [container_row(p) for p in splits["C_generator_holdout"]["test"]]
    split_c_test = [r for r in split_c_test if r]
    split_c_train = [container_row(p) for p in splits["C_generator_holdout"]["train"]]
    split_c_train = [r for r in split_c_train if r]

    # ---------- P1: non-pixel shortcut on Split C -------------------
    print()
    print("=== P1: NON-PIXEL classifier on Split C (no image content used) ===")
    container_features = ["width", "height", "long_edge", "short_edge",
                          "aspect_ratio", "size_bytes", "bytes_per_pixel", "crop_loss"]
    p1 = auc_of(split_c_train + split_c_test, container_features,
                "all container features (train+test pooled)")
    findings["p1_non_pixel_auc"] = p1

    print()
    print("=== P1b: which single feature leaks most? ===")
    singles = {}
    for feature in container_features:
        auc = auc_of(split_c_train + split_c_test, [feature], f"{feature} alone")
        singles[feature] = auc
    findings["p1_single_features"] = singles

    # ---------- P2: source-only ------------------------------------
    print()
    print("=== P2: SOURCE-only classifier (dataset identity, no pixels) ===")
    p2 = auc_of(split_c_train + split_c_test, ["source_flickr"],
                "is_flickr30k alone")
    findings["p2_source_only_auc"] = p2

    # ---------- P3: container probe per split ----------------------
    print()
    print("=== P3: container shortcut AUC per split ===")
    p3 = {}
    for name, split in splits.items():
        rows = [container_row(p) for p in split["test"]]
        rows = [r for r in rows if r]
        p3[name] = auc_of(rows, container_features, f"{name} test")
    findings["p3_container_per_split"] = p3

    # ---------- P4: label permutation ------------------------------
    print()
    print("=== P4: label permutation sanity (shuffled labels must be ~0.5) ===")
    rows = list(split_c_train + split_c_test)
    labels = np.asarray([r["label"] for r in rows])
    rng = np.random.RandomState(SEED)
    shuffled = labels.copy()
    rng.shuffle(shuffled)
    X = np.asarray([[float(r[f]) for f in container_features] for r in rows])
    X_train, X_test, y_train, y_test = train_test_split(
        X, shuffled, test_size=0.3, random_state=SEED
    )
    model = LogisticRegression(max_iter=3000, random_state=SEED)
    model.fit(X_train, y_train)
    p4 = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
    print(f"    shuffled-label container AUC            = {p4:.4f}  (expect ~0.5)")
    findings["p4_label_permutation_auc"] = p4

    # ---------- P5: matched-source subset --------------------------
    print()
    print("=== P5: MATCHED-SOURCE subset (format + resolution + aspect matched) ===")
    def bin_resolution(value: int) -> str:
        for edge in (128, 192, 224, 256, 320, 384, 512, 768, 1024):
            if value <= edge:
                return f"<={edge}"
        return ">1024"

    def bin_aspect(value: float) -> str:
        if value < 0.95:
            return "portrait"
        if value < 1.05:
            return "square"
        return "landscape"

    for row in rows:
        row["res_bin"] = bin_resolution(row["long_edge"])
        row["aspect_bin"] = bin_aspect(row["aspect_ratio"])

    real_rows = [r for r in rows if r["label"] == 0]
    syn_rows = [r for r in rows if r["label"] == 1]

    # For each synthetic row, keep it only if a real row shares its
    # (format, resolution bin, aspect bin). That is the matched subset.
    real_keys: Counter = Counter(
        (r["format"], r["res_bin"], r["aspect_bin"]) for r in real_rows
    )
    matched_syn = [
        r for r in syn_rows
        if real_keys[(r["format"], r["res_bin"], r["aspect_bin"])] > 0
    ]
    # Sample an equal number of real rows from the same cells.
    matched_real: list[dict] = []
    needed: Counter = Counter(
        (r["format"], r["res_bin"], r["aspect_bin"]) for r in matched_syn
    )
    pool = list(real_rows)
    rng2 = random.Random(SEED)
    rng2.shuffle(pool)
    for row in pool:
        key = (row["format"], row["res_bin"], row["aspect_bin"])
        if needed[key] > 0:
            needed[key] -= 1
            matched_real.append(row)

    print(f"    synthetic rows with a matching real cell: {len(matched_syn):,}/{len(syn_rows):,}")
    print(f"    matched real rows selected              : {len(matched_real):,}")
    p5 = auc_of(matched_real + matched_syn, container_features,
                "container AUC on matched subset")
    findings["p5_matched_subset"] = {
        "synthetic_with_matching_real_cell": len(matched_syn),
        "synthetic_total": len(syn_rows),
        "real_selected": len(matched_real),
        "container_auc": p5,
    }

    # ---------- P6: crop-loss probe --------------------------------
    print()
    print("=== P6: does crop-area-loss alone predict the label? ===")
    crop_values = {round(r["crop_loss"], 6) for r in rows}
    print(f"    distinct crop_loss values after square normalization: {len(crop_values)}")
    p6 = auc_of(rows, ["crop_loss"], "crop_loss alone")
    findings["p6_crop_loss_auc"] = p6

    # ---------- write CSVs ------------------------------------------
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "split_c_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "label", "source", "format", "width", "height",
                        "long_edge", "short_edge", "aspect_ratio", "size_bytes",
                        "bytes_per_pixel", "crop_loss", "res_bin", "aspect_bin", "source_flickr"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print()
    print(f"written: {RESULTS / 'split_c_audit.csv'}  ({len(rows):,} rows)")

    with (RESULTS / "split_c_shortcut_probe.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["probe", "auc", "interpretation"])
        writer.writerow(["p1_non_pixel_all_container", p1,
                         "container features only, pooled A+B+C rows"])
        for feature, value in singles.items():
            writer.writerow([f"p1_single_{feature}", value, "single feature"])
        writer.writerow(["p2_source_only", p2, "dataset identity only"])
        for name, value in p3.items():
            writer.writerow([f"p3_container_{name}", value, "per-split container probe"])
        writer.writerow(["p4_label_permutation", p4, "expect ~0.5"])
        writer.writerow(["p5_matched_subset_container", findings["p5_matched_subset"]["container_auc"],
                         "container AUC after matching format/res/aspect"])
        writer.writerow(["p6_crop_loss_only", p6, "crop-area-loss alone"])
    print(f"written: {RESULTS / 'split_c_shortcut_probe.csv'}")

    # ---------- verdict ---------------------------------------------
    print()
    print("=== VERDICT ON THE 0.9988 ===")
    thresholds = {
        "p1_non_pixel": (p1, 0.80),
        "p2_source_only": (p2, 0.80),
        "p4_label_permutation": (p4, 0.60),
        "p6_crop_loss": (p6, 0.75),
        "p5_matched_container": (p5, 0.75),
    }
    failed = []
    for name, (value, limit) in thresholds.items():
        if value is not None and abs(value - 0.5) > (limit - 0.5):
            failed.append(f"{name}={value:.4f} (limit {limit})")
    worst_split = max(
        ((n, v) for n, v in p3.items() if v is not None), key=lambda kv: kv[1], default=(None, None)
    )
    if worst_split and worst_split[1] > 0.85:
        failed.append(f"p3 container probe {worst_split[0]}={worst_split[1]:.4f}")

    findings["failed_probes"] = failed
    findings["verdict"] = "SHORTCUT DRIVEN" if failed else "NO SHORTCUT DETECTED"
    (RESULTS / "split_c_investigation.json").write_text(
        json.dumps(findings, indent=2), encoding="utf-8"
    )
    print(f"  verdict: {findings['verdict']}")
    if failed:
        print("  failed probes:")
        for item in failed:
            print(f"    - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())