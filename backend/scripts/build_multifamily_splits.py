"""
Build the unified multi-family corpus and strict family-holdout splits.

Two sources, kept as separate columns and never silently merged:

  CommunityForensics (via datasets/image/square/)
    - 400 real, 2,212 synthetic, 547 documented generator labels
    - 99.3% LatDiff
  AIGC-Detection-Benchmark (via datasets/image/crossfamily/)
    - 900 real, 4,299 synthetic across GAN / PixelDiffusion / LatDiff /
      Unknown_Architecture (Midjourney)
    - license Apache-2.0 at the HF mirror, upstream provenance
      documented only per constituent image

Both directories are already normalized:
  * square/      - centre-cropped exact 256x256 JPEG q90
  * crossfamily/ - letterboxed  256x256 JPEG q90
Container shortcut probe after normalization: 0.5363 (crossfamily) and
0.6209 (CommunityForensics). Both below the 0.85 blocking threshold.

That difference in normalization between the two sources is itself a
source cue, so it is recorded per row and measured by the source
classifier rather than assumed harmless.

Family-holdout experiments
--------------------------
  A  train LatDiff + PixelDiffusion   -> test GAN
  B  train LatDiff + GAN              -> test PixelDiffusion
  C  train GAN + PixelDiff + LatDiff  -> test Midjourney (Unknown)
  D  train GAN + PixelDiff            -> test LatDiff
  E  train all but SDXL               -> test SDXL (single major generator)

Real images are drawn from BOTH sources and partitioned independently, so
no experiment becomes "all real from source A, all synthetic from source
B". Where a held-out family exists in only one source, the real pool
still spans both.

Leakage is asserted and aborts the build.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
SQUARE = BACKEND / "datasets" / "image" / "square"
CROSSFAM = BACKEND / "datasets" / "image" / "crossfamily"
CF_RECORDS = BACKEND / "datasets" / "image" / "manifests" / "_cf_records.json"
CF_INDEX = BACKEND / "results" / "phase3" / "crossfamily_index.csv"
RESULTS = BACKEND / "results" / "phase3"

SEED = 42

EXPERIMENTS = {
    "A_holdout_GAN": {"train_families": ["LatDiff", "PixelDiffusion"], "test_family": "GAN"},
    "B_holdout_PixelDiffusion": {"train_families": ["LatDiff", "GAN"], "test_family": "PixelDiffusion"},
    "C_holdout_Midjourney": {"train_families": ["GAN", "PixelDiffusion", "LatDiff"],
                             "test_family": "Unknown_Architecture"},
    "D_holdout_LatDiff": {"train_families": ["GAN", "PixelDiffusion"], "test_family": "LatDiff"},
    "E_holdout_SDXL": {"train_families": ["GAN", "PixelDiffusion", "LatDiff"],
                       "test_family": "LatDiff", "exclude_generator": "SDXL"},
}


def perceptual_group(relative: str) -> str:
    return hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest()


def cf_generator_for(path: Path, mapping: dict[str, dict]) -> str | None:
    original = path.name.split("__", 1)[-1]
    for candidate in (original, original.removesuffix(".jpg"), original.removesuffix(".png")):
        record = mapping.get(candidate)
        if record:
            return record.get("generator")
    return None


def load_cf() -> list[dict]:
    mapping = {}
    for record in json.loads(CF_RECORDS.read_text(encoding="utf-8")):
        mapping[Path(record["path"]).name] = record

    rows = []
    for path in sorted(SQUARE.rglob("*.jpg")):
        label = 1 if "synthetic" in path.parts else 0
        relative = str(path.relative_to(PROJECT)).replace("\\", "/")
        generator = cf_generator_for(path, mapping) if label else None
        family = (mapping.get(path.name.split("__", 1)[-1], {}) or {}).get("generator_family")
        rows.append({
            "path": relative,
            "label": label,
            "source": "communityforensics",
            "family": family or ("real" if label == 0 else "unknown"),
            "generator": generator or ("real" if label == 0 else "unknown"),
            "normalization": "centre_crop_square",
        })
    return rows


def load_crossfamily() -> list[dict]:
    rows = []
    for record in csv.DictReader(CF_INDEX.open(encoding="utf-8")):
        generator = record["generator"]
        family = record["family"]
        if int(record["label"]) == 0:
            generator, family = "real", "real"
        rows.append({
            "path": record["path"],
            "label": int(record["label"]),
            "source": "aigcdetection_benchmark",
            "family": family,
            "generator": generator,
            "normalization": "letterbox",
        })
    return rows


def main() -> int:
    rng = random.Random(SEED)
    rows = load_cf() + load_crossfamily()
    for row in rows:
        row["label"] = int(row["label"])
    print(f"unified corpus: {len(rows):,} images")
    print(f"  real={sum(1 for r in rows if r['label'] == 0):,}  "
          f"synthetic={sum(1 for r in rows if r['label'] == 1):,}")
    print(f"  sources: {dict(Counter(r['source'] for r in rows))}")
    print(f"  families: {dict(Counter(r['family'] for r in rows))}")

    real_rows = [r for r in rows if r["label"] == 0]
    syn_rows = [r for r in rows if r["label"] == 1]
    rng.shuffle(real_rows)

    # Real pool partitioned ONCE, then reused by every experiment, so real
    # images never appear in both a training and a test set of the same
    # experiment.
    n = len(real_rows)
    real_train = real_rows[: int(n * 0.55)]
    real_val = real_rows[int(n * 0.55) : int(n * 0.70)]
    real_test = real_rows[int(n * 0.70) :]
    print(f"\n  real pool: train={len(real_train)} val={len(real_val)} test={len(real_test)}")
    print(f"    real test by source: "
          f"{dict(Counter(r['source'] for r in real_test))}")

    by_family: dict[str, list[dict]] = {}
    for row in syn_rows:
        by_family.setdefault(row["family"], []).append(row)
    for family, items in by_family.items():
        rng.shuffle(items)

    def take(family: str, exclude_generator: str | None, fraction: float = 1.0) -> list[dict]:
        items = [i for i in by_family.get(family, []) if i["generator"] != exclude_generator]
        return items[: int(len(items) * fraction)]

    experiments = {}
    print()
    for name, spec in EXPERIMENTS.items():
        exclude = spec.get("exclude_generator")
        train_syn = []
        for family in spec["train_families"]:
            train_syn.extend(take(family, exclude))
        # Validation uses training families only - never the held-out one.
        rng.shuffle(train_syn)
        cut = int(0.85 * len(train_syn))
        syn_train, syn_val = train_syn[:cut], train_syn[cut:]

        if spec["test_family"] == "LatDiff" and exclude:
            test_syn = [i for i in by_family["LatDiff"] if i["generator"] == exclude]
            test_label = f"{spec['test_family']}/{exclude}"
        else:
            test_syn = list(by_family.get(spec["test_family"], []))
            test_label = spec["test_family"]

        if not test_syn:
            print(f"  {name:28} SKIPPED - no images for {spec['test_family']}")
            continue

        train = real_train + syn_train
        val = real_val + syn_val
        test = real_test + test_syn

        # ---- leakage assertions (abort on violation) ----------------
        train_paths = {r["path"] for r in train}
        test_paths = {r["path"] for r in test}
        assert not (train_paths & test_paths), f"{name}: path overlap"
        assert not ({r['path'] for r in real_train} & {r['path'] for r in real_test}), \
            f"{name}: real image overlap"

        if spec["test_family"] and not exclude:
            train_families = {r["family"] for r in syn_train}
            assert spec["test_family"] not in train_families, \
                f"{name}: held-out family leaked into training"

        train_generators = {r["generator"] for r in syn_train}
        test_generators = {r["generator"] for r in test_syn}
        assert not (train_generators & test_generators), f"{name}: generator overlap"

        experiments[name] = {
            "train": [r["path"] for r in train],
            "val": [r["path"] for r in val],
            "test": [r["path"] for r in test],
            "held_out_family": spec["test_family"],
            "held_out_generator": exclude,
            "held_out_label": test_label,
            "train_families": spec["train_families"],
            "counts": {
                "train": {"real": len(real_train), "synthetic": len(syn_train)},
                "val": {"real": len(real_val), "synthetic": len(syn_val)},
                "test": {"real": len(real_test), "synthetic": len(test_syn)},
            },
            "test_synthetic_by_generator": dict(
                Counter(r["generator"] for r in test_syn)),
        }
        c = experiments[name]["counts"]
        print(f"  {name:28} train {c['train']['real']:>5}r/{c['train']['synthetic']:>5}s  "
              f"test {c['test']['real']:>4}r/{c['test']['synthetic']:>5}s  "
              f"(holds out {test_label})")

    # ---- persist ---------------------------------------------------
    with (RESULTS / "multifamily_corpus.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "label", "source", "family",
                                                    "generator", "normalization"])
        writer.writeheader()
        writer.writerows(rows)

    (RESULTS / "multifamily_splits.json").write_text(json.dumps({
        "seed": SEED,
        "corpus_size": len(rows),
        "sources": dict(Counter(r["source"] for r in rows)),
        "families": dict(Counter(r["family"] for r in rows)),
        "normalization": {
            "communityforensics": "centre-crop exact 256x256 JPEG q90 (shortcut AUC 0.6209)",
            "aigcdetection_benchmark": "letterbox 256x256 JPEG q90 (shortcut AUC 0.5363)",
            "class_symmetric": True,
            "note": ("The two sources use DIFFERENT normalization policies, which is "
                     "itself a source cue. It is measured by the source classifier "
                     "rather than assumed harmless."),
        },
        "real_pool": {"train": len(real_train), "val": len(real_val), "test": len(real_test)},
        "experiments": experiments,
    }, indent=2), encoding="utf-8")

    print()
    print(f"written: {RESULTS / 'multifamily_corpus.csv'}")
    print(f"written: {RESULTS / 'multifamily_splits.json'}")
    print(f"experiments built: {len(experiments)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())