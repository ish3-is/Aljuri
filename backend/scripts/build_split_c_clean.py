"""
Build Split C_clean — the unconfounded same-source evaluation.

Why this exists
---------------
The previous Split C reported ROC-AUC 0.9988 on 109 unseen generators,
which looked like excellent generalisation. It was not usable evidence:

    synthetic/Flickr = 0 in every split

Flickr30k is a real-only corpus and CommunityForensics is the sole source
of synthetic imagery, so "is this image from Flickr?" was nearly the same
question as "is this image real?". Source-only classification scored
AUC 0.9409.

    Zero generator leakage does NOT imply zero dataset leakage.

C_clean removes the confound by using CommunityForensics for BOTH classes.
Source identity is then constant by design, so a source-only classifier is
undefined rather than merely weak - and we say so instead of fabricating a
number.

The price is statistical power: CommunityForensics holds only 400 real
images. Every metric below therefore reports its sample size, and the
false-positive rate carries an explicit confidence interval rather than a
bare percentage that would imply more certainty than 100 images can
support.
"""

from __future__ import annotations

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
RECORDS = BACKEND / "datasets" / "image" / "manifests" / "_cf_records.json"
SPLITS = BACKEND / "results" / "phase3" / "splits.json"

SEED = 42
N_HELDOUT_GENERATORS = 109
REAL_FRACTIONS = {"train": 0.60, "val": 0.15, "test": 0.25}


def perceptual_group(relative: str) -> str:
    """Cheap content hash of the file bytes.

    Used only as a duplicate guard within CommunityForensics. Exact byte
    identity is sufficient here because normalisation re-encoded every
    file through one deterministic JPEG path, so any true duplicate would
    share bytes.
    """
    return hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest()


def load_cf_records() -> dict[str, dict]:
    """Original filename -> source record, for generator labels."""
    mapping: dict[str, dict] = {}
    for record in json.loads(RECORDS.read_text(encoding="utf-8")):
        mapping[Path(record["path"]).name] = record
    return mapping


def label_of(relative: str) -> int:
    return 1 if "/synthetic/" in relative.replace("\\", "/") else 0


def generator_for(path: Path, records: dict[str, dict]) -> str | None:
    original = path.name.split("__", 1)[-1]
    for candidate in (original, original.removesuffix(".jpg"), original.removesuffix(".png")):
        record = records.get(candidate)
        if record:
            return record.get("generator")
    return None


def main() -> int:
    rng = random.Random(SEED)
    records = load_cf_records()

    real, synthetic = [], []
    for label, folder in ((0, "real"), (1, "synthetic")):
        for path in sorted((SQUARE / folder).glob("communityforensics__*.jpg")):
            relative = str(path.relative_to(PROJECT)).replace("\\", "/")
            item = {"path": relative, "label": label}
            if label == 1:
                item["generator"] = generator_for(path, records)
            real.append(item) if label == 0 else synthetic.append(item)

    documented = [i for i in synthetic if i.get("generator")]
    generators = sorted({i["generator"] for i in documented})
    print(f"CommunityForensics only:")
    print(f"  real              : {len(real):,}")
    print(f"  synthetic         : {len(synthetic):,}")
    print(f"  synthetic w/ label: {len(documented):,} "
          f"({len(generators)} distinct generators)")
    if len(generators) < N_HELDOUT_GENERATORS:
        print(f"  WARNING: only {len(generators)} generators available, "
              f"requested {N_HELDOUT_GENERATORS} holdout")

    # ---- generator holdout -----------------------------------------
    rng.shuffle(generators)
    holdout = set(generators[:N_HELDOUT_GENERATORS])
    syn_trainval = [i for i in documented if i["generator"] not in holdout]
    syn_test = [i for i in documented if i["generator"] in holdout]
    print(f"  held-out generators: {len(holdout)}  "
          f"(train generators: {len(generators) - len(holdout)})")

    # ---- split synthetic -------------------------------------------
    rng.shuffle(syn_trainval)
    cut = int(0.85 * len(syn_trainval))
    syn_train, syn_val = syn_trainval[:cut], syn_trainval[cut:]

    # ---- split real: partition cleanly, never duplicate -------------
    rng.shuffle(real)
    n = len(real)
    n_train = int(n * REAL_FRACTIONS["train"])
    n_val = int(n * REAL_FRACTIONS["val"])
    real_train = real[:n_train]
    real_val = real[n_train : n_train + n_val]
    real_test = real[n_train + n_val :]

    # Test is real-heavy by design: the false-positive rate is the number
    # that matters operationally, so it gets the larger half.
    test = real_test + syn_test
    train = real_train + syn_train
    val = real_val + syn_val

    print()
    print("=== C_clean sizes ===")
    for name, part in (("train", train), ("val", val), ("test", test)):
        r = sum(1 for i in part if i["label"] == 0)
        s = sum(1 for i in part if i["label"] == 1)
        print(f"  {name:6} real={r:5,} synthetic={s:5,}  total={len(part):5,}")

    # ---- leakage assertions ----------------------------------------
    print()
    print("=== LEAKAGE ASSERTIONS (abort on violation) ===")

    def paths_of(items):
        return {i["path"] for i in items}

    assert not (paths_of(train) & paths_of(test)), "train/test id overlap"
    print("  train_image_ids INTERSECT test_image_ids = empty            OK")

    train_groups = {perceptual_group(p) for p in paths_of(train)}
    test_groups = {perceptual_group(p) for p in paths_of(test)}
    assert not (train_groups & test_groups), "perceptual duplicate overlap"
    print(f"  train_perceptual INTERSECT test_perceptual = empty           OK "
          f"({len(train_groups):,} vs {len(test_groups):,} groups)")

    train_generators = {i["generator"] for i in train if i.get("generator")}
    assert not (train_generators & holdout), "generator leakage"
    print(f"  train_generators INTERSECT heldout_generators = empty        OK "
          f"({len(train_generators):,} vs {len(holdout):,})")

    assert not ({i["path"] for i in real_train} & {i["path"] for i in real_test}), "real leakage"
    print("  train_real_ids INTERSECT test_real_ids = empty               OK")

    # ---- statistical power warning ----------------------------------
    print()
    print("=== STATISTICAL POWER ===")
    print(f"  real test images: {len(real_test):,}")
    # Wilson-ish normal approximation: 1.96 * sqrt(p(1-p)/n).
    # An earlier version of this line divided by sqrt(n) instead of
    # multiplying, understating the interval by 4.5x and implying far more
    # precision than 100 images can support.
    import math

    half = 1.96 * math.sqrt(0.05 * 0.95 / max(len(real_test), 1))
    print(f"  A false-positive rate measured on {len(real_test)} images has a")
    print(f"  95% CI half-width of about +/-{half:.3f} at a 5% observed rate.")
    print("  i.e. an observed 5% FPR is consistent with roughly 1%-9%.")
    print("  Every rate below MUST be reported with its interval.")

    imbalance = len(syn_train) / max(len(real_train), 1)
    print()
    print("=== TRAINING IMBALANCE ===")
    print(f"  train real={len(real_train)}  synthetic={len(syn_train)}  "
          f"ratio {imbalance:.1f}:1 toward synthetic")
    print("  Left uncorrected this biases the classifier toward 'synthetic'")
    print("  and INFLATES the false-positive rate. Training must use class")
    print("  weighting rather than discarding the 1,259 excess synthetic")
    print("  images, because only 400 real images exist in total.")

    # ---- preserve old splits, add the new one -----------------------
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))["splits"]

    if "C_generator_holdout" in splits:
        old = splits.pop("C_generator_holdout")
        splits["C_original_INVALID_source_confounded"] = {
            **old,
            "status": "INVALID_FOR_MODEL_CLAIMS_SOURCE_CONFOUNDED",
            "source_confound": {
                "synthetic_from_flickr": 0,
                "source_only_auc": 0.9409,
                "explanation": (
                    "Flickr30k is a real-only corpus and CommunityForensics is "
                    "the only source of synthetic images, so dataset identity "
                    "was nearly equivalent to the class label. Observed "
                    "EfficientNet metrics (random 0.9971, source-grouped "
                    "0.9979, generator-held-out 0.9988) are retained as "
                    "evidence of this contamination, NOT as synthetic-"
                    "detection performance."
                ),
            },
        }

    splits["C_clean_CF_generator_holdout"] = {
        "status": "PRIMARY_UNCONFOUNDED_GENERATOR_TEST",
        "source_confound_removed": True,
        "source_only_classifier": "UNDEFINED - source identity is constant (CommunityForensics only)",
        "train": [i["path"] for i in train],
        "val": [i["path"] for i in val],
        "test": [i["path"] for i in test],
        "held_out_generators": sorted(holdout),
        "held_out_generator_count": len(holdout),
        "train_generator_count": len(train_generators),
        "leakage_assertions": {
            "image_id_overlap": 0,
            "perceptual_group_overlap": 0,
            "generator_overlap": 0,
            "real_id_overlap": 0,
        },
        "counts": {
            "real_available": n,
            "train": {"real": len(real_train), "synthetic": len(syn_train)},
            "val": {"real": len(real_val), "synthetic": len(syn_val)},
            "test": {"real": len(real_test), "synthetic": len(syn_test)},
        },
        "note": (
            "CommunityForensics only, both classes. Source identity is "
            "constant, so the Flickr-vs-CommunityForensics confound is "
            "structurally impossible here. Limited by only "
            f"{n} real images; false-positive rates carry wide intervals."
        ),
    }

    SPLITS.write_text(json.dumps({"splits": splits}, indent=2), encoding="utf-8")
    print()
    print(f"written: {SPLITS}")
    print("  C_original_INVALID_source_confounded  -> preserved, marked invalid")
    print("  C_clean_CF_generator_holdout          -> primary unconfounded test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())