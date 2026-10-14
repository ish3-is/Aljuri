"""
Build Phase 3 splits, with a generator-held-out evaluation.

Four splits, in increasing order of how much they actually test:

A. **random stratified**          - the number everyone quotes, and the
                                    least informative.
B. **source-grouped**             - no Flickr real image in train if a
                                    Flickr real image is in test.
C. **generator-held-out**         - the synthetic generators in test are
                                    entirely absent from training. This is
                                    the one that answers "will this work on
                                    a generator it has never seen".
D. **cross-dataset**              - train on CommunityForensics only,
                                    test on Flickr real, and the reverse.

Why C matters more than A
-------------------------
CommunityForensics documents 547 distinct generators, all sourced from
the source data rather than inferred. That makes a genuine leave-
generators-out split possible. Random splitting would put near-identical
generator outputs on both sides and report a number that means nothing.

Class balance
-------------
Raw counts are ~2.7:1 real-heavy (3,399 real vs 2,212 synthetic). Left
alone, accuracy rewards predicting "real". Both the train and test sets
are balanced by downsampling the majority class, and the discarded count
is reported rather than hidden.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SQUARE = BACKEND / "datasets" / "image" / "square"
RECORDS = BACKEND / "datasets" / "image" / "manifests" / "_cf_records.json"
OUT = BACKEND / "results" / "phase3"
SEED = 42


def load_items() -> list[dict]:
    """Join normalized files on disk with the source's generator labels."""
    items: list[dict] = []

    for label, folder in ((0, "real"), (1, "synthetic")):
        for path in sorted((SQUARE / folder).glob("*.jpg")):
            source = "flickr30k" if path.name.startswith("flickr30k__") else "communityforensics"
            items.append({
                "path": path,
                "label": label,
                "source": source,
                "generator": None,
                "generator_family": None,
            })

    if not RECORDS.exists():
        return items

    # Map original filename -> generator metadata, then re-attach after
    # normalization renamed the files with a source prefix.
    by_name: dict[str, dict] = {}
    for record in json.loads(RECORDS.read_text(encoding="utf-8")):
        original = Path(record["path"]).name
        by_name[original] = record

    matched = 0
    for item in items:
        if item["source"] != "communityforensics":
            continue
        original = item["path"].name.split("__", 1)[-1].replace(".jpg", "")
        record = by_name.get(original)
        if record is None:
            # Normalization appended .jpg to an original .png name.
            record = by_name.get(original + ".png") or by_name.get(original + ".jpg")
        if record is None:
            continue
        item["generator"] = record.get("generator")
        item["generator_family"] = record.get("generator_family")
        matched += 1

    return items


def balanced(synthetic: list[dict], real: list[dict], rng: random.Random) -> tuple[list[dict], dict]:
    """Downsample the majority class so neither dominates."""
    rng.shuffle(synthetic)
    rng.shuffle(real)
    n = min(len(synthetic), len(real))
    chosen = synthetic[:n] + real[:n]
    stats = {
        "synthetic_available": len(synthetic),
        "real_available": len(real),
        "synthetic_used": n,
        "real_used": n,
        "real_discarded": len(real) - n,
        "synthetic_discarded": len(synthetic) - n,
    }
    return chosen, stats


def main() -> int:
    rng = random.Random(SEED)
    items = load_items()
    if not items:
        print("no images found")
        return 1

    synthetic = [i for i in items if i["label"] == 1]
    real = [i for i in items if i["label"] == 0]

    print(f"images on disk : {len(items):,}  (real={len(real):,} synthetic={len(synthetic):,})")
    documented = [i for i in synthetic if i.get("generator")]
    print(f"with generator label: {len(documented):,} "
          f"({len({i['generator'] for i in documented})} distinct)")
    families = Counter(i.get("generator_family") for i in synthetic)
    print(f"generator families: {dict(families)}")

    report: dict = {
        "seed": SEED,
        "available": {"real": len(real), "synthetic": len(synthetic)},
        "generator_coverage": {
            "documented": len(documented),
            "distinct_generators": len({i["generator"] for i in documented}),
            "families": dict(families),
            "note": (
                "Generator labels come from the source dataset's own columns. "
                "None were inferred from filenames or content."
            ),
        },
        "splits": {},
    }

    # ---- A: random stratified -------------------------------------
    balanced_items, stats = balanced(list(synthetic), list(real), rng)
    print()
    print(f"balanced pool  : {len(balanced_items):,} "
          f"(discarded real={stats['real_discarded']:,} "
          f"synthetic={stats['synthetic_discarded']:,})")
    rng.shuffle(balanced_items)
    cut_a = int(0.7 * len(balanced_items))
    cut_b = cut_a + int(0.15 * len(balanced_items))
    report["splits"]["A_random_stratified"] = {
        "train": [str(i["path"].relative_to(BACKEND.parent)) for i in balanced_items[:cut_a]],
        "val": [str(i["path"].relative_to(BACKEND.parent)) for i in balanced_items[cut_a:cut_b]],
        "test": [str(i["path"].relative_to(BACKEND.parent)) for i in balanced_items[cut_b:]],
        "balance": stats,
    }

    # ---- B: source-grouped ----------------------------------------
    # Test = Flickr real + a slice of CommunityForensics. Training keeps
    # NO Flickr image, so the model must recognise unseen real photos.
    cf_synth = [i for i in synthetic if i["source"] == "communityforensics"]
    flickr_real = [i for i in real if i["source"] == "flickr30k"]
    cf_real = [i for i in real if i["source"] == "communityforensics"]
    rng.shuffle(cf_synth)
    n_test_synth = max(1, len(cf_synth) // 5)
    test_synth = cf_synth[:n_test_synth]
    train_pool = cf_synth[n_test_synth:] + cf_real
    n_test_real = max(1, int(len(flickr_real) * 0.2))
    test_real = flickr_real[:n_test_real]
    train_real_pool = flickr_real[n_test_real:]
    # Balance the training set; the test set is left in its natural mix
    # so FPR on real-world photography is measured honestly.
    train_balanced, b_stats = balanced(list(train_pool), list(train_real_pool), rng)
    report["splits"]["B_source_grouped"] = {
        "train": [str(i["path"].relative_to(BACKEND.parent)) for i in train_balanced],
        "val": [],
        "test": [str(i["path"].relative_to(BACKEND.parent)) for i in (test_synth + test_real)],
        "note": (
            "No Flickr image appears in training. The test set keeps its "
            "natural real-heavy mix so the false-positive rate on real "
            "photography is not flattered by balancing."
        ),
        "balance": b_stats,
    }

    # ---- C: generator-held-out ------------------------------------
    if documented:
        generators = sorted({i["generator"] for i in documented})
        rng.shuffle(generators)
        n_holdout = max(1, len(generators) // 5)
        holdout = set(generators[:n_holdout])
        train_gens = [i for i in documented if i["generator"] not in holdout]
        test_gens = [i for i in documented if i["generator"] in holdout]
        # Real images are REQUIRED in training. An earlier version built
        # this split from synthetic items alone, producing a training set
        # with zero real examples - the model would have learned nothing
        # and any score would have been meaningless.
        rng.shuffle(real)
        n_real_test = max(1, len(real) // 5)
        test_real = real[:n_real_test]
        train_real = real[n_real_test:]
        # Balance the training pool across classes.
        train_balanced_c, c_stats = balanced(list(train_gens), list(train_real), rng)
        # Balance the test set too, so FPR and FNR are both meaningful.
        test_balanced_c, _ = balanced(list(test_gens), list(test_real), rng)
        report["splits"]["C_generator_holdout"] = {
            "held_out_generators": sorted(holdout),
            "held_out_generator_count": len(holdout),
            "train_generators": len(generators) - len(holdout),
            "train": [str(i["path"].relative_to(BACKEND.parent)) for i in train_balanced_c],
            "val": [],
            "test": [str(i["path"].relative_to(BACKEND.parent)) for i in test_balanced_c],
            "balance": c_stats,
            "note": (
                f"{len(holdout)} of {len(generators)} generators are held out "
                "entirely. Synthetic images in the test set come from "
                "generators never seen in training."
            ),
        }
        print(f"generator holdout: {len(holdout)}/{len(generators)} generators "
              f"({len(test_gens):,} synthetic test images)")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "splits.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    for name, split in report["splits"].items():
        print(f"  {name:28} train={len(split['train']):6,}  test={len(split['test']):6,}")
    print(f"\nwritten: {OUT / 'splits.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())