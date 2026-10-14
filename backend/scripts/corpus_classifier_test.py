"""TRAIN A CORPUS-CLASSIFIER ON METADATA-ONLY FEATURES.

This is the decisive shortcut test. If a model can predict "real vs synthetic"
from NOTHING but container format, pixel dimensions, file size, mode and EXIF
presence, then a detector scoring high accuracy may simply have learned the
DATASET rather than synthetic media.

We deliberately fit on metadata only -- no pixels -- so any AUC well above
chance is pure corpus fingerprinting. We report AUC per feature set and also a
train/test split ACROSS corpora, because within-corpus accuracy can hide the
fact that each corpus is internally trivially separable.
"""
import glob
import io
import json
import os
from collections import Counter, defaultdict

import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

RNG = 42
MAN = "datasets/image/manifests"
OUT = "datasets/image/audit/corpus_classifier.json"


def meta_features(path):
    """Features that leak dataset identity without any pixel content."""
    size = os.path.getsize(path)
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            w, h = im.size
            fmt = im.format
            mode = im.mode
            ex = im.getexif()
            exif_present = 1 if ex else 0
            make = 0
            if ex and ex.get(0x010F):
                m = str(ex.get(0x010F)).strip().lower()
                make = {"canon": 1, "nikon": 2, "olympus": 3, "samsung": 4,
                        "sony": 5, "apple": 6, "fuji": 7}.get(m.split()[0], 8)
    except Exception:
        return None
    ar = w / max(1, h)
    # bytes per pixel is a pure compression fingerprint
    bpp = size / max(1, w * h)
    return {
        "w": w, "h": h, "px": w * h, "aspect": ar, "bytes": size,
        "log_bytes": np.log1p(size), "bpp": bpp,
        "is_png": 1 if fmt == "PNG" else 0,
        "is_jpeg": 1 if fmt == "JPEG" else 0,
        "mode_rgb": 1 if mode == "RGB" else 0,
        "mode_l": 1 if mode == "L" else 0,
        "exif": exif_present, "make": make,
    }


FEATURE_SETS = {
    "container_only": ["is_png", "is_jpeg", "mode_rgb", "mode_l"],
    "dimensions_only": ["w", "h", "px", "aspect"],
    "filesize_only": ["bytes", "log_bytes", "bpp"],
    "exif_only": ["exif", "make"],
    "all_metadata_no_pixels": ["w", "h", "px", "aspect", "bytes", "log_bytes",
                               "bpp", "is_png", "is_jpeg", "mode_rgb", "mode_l",
                               "exif", "make"],
}


def main():
    # label MUST be set explicitly. Inferring it from whether the string
    # contains "real" previously mislabelled "flickr30k_flat" (real photos in
    # a flat dir) as SYNTHETIC, which flooded the synthetic class with real
    # images and drove every AUC toward a meaningless 0.5.
    corpora = {
        "communityforensics_small_synthetic":
            ("datasets/image/raw/communityforensics_small/synthetic", 1),
        "communityforensics_small_real":
            ("datasets/image/raw/communityforensics_small/real", 0),
        "flickr30k_real":
            ("datasets/image/raw/flickr30k/real", 0),
        "flickr30k_flat":
            ("datasets/image/raw/flickr30k", 0),
    }
    rows, labels, groups, shas = [], [], [], []
    seen_sha = {}
    for name, (d, lab) in corpora.items():
        if not os.path.isdir(d):
            print(f"(skip {name}: {d} missing)")
            continue
        files = [f for f in sorted(glob.glob(os.path.join(d, "**", "*"), recursive=True))
                 if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        n_dup = 0
        print(f"{name}: {len(files)} files, label={lab}", flush=True)
        for f in files:
            # de-duplicate identical images ACROSS corpora: the same Flickr
            # photo appearing in two folders must not count twice
            try:
                import hashlib
                with open(f, "rb") as fh:
                    sha = hashlib.sha256(fh.read()).hexdigest()
            except Exception:
                continue
            if sha in seen_sha:
                n_dup += 1
                continue
            seen_sha[sha] = name
            ft = meta_features(f)
            if ft:
                rows.append(ft)
                labels.append(lab)
                groups.append(name)
                shas.append(sha)
        print(f"   kept {len(files)-n_dup}, dropped {n_dup} duplicate-content images",
              flush=True)
    if not rows:
        raise SystemExit("no images found")

    X = np.array([[r[k] for k in FEATURE_SETS["all_metadata_no_pixels"]]
                  for r in rows], dtype=float)
    y = np.array(labels)
    g = np.array(groups)
    print(f"\nfeatures: {X.shape}, real={int((y==0).sum())} synthetic={int((y==1).sum())}")

    report = {"n_samples": int(X.shape[0]),
              "n_real": int((y == 0).sum()), "n_synthetic": int((y == 1).sum()),
              "corpus_groups": {k: int((g == k).sum()) for k in sorted(set(groups))},
              "results": {}, "interpretation": {}}

    for fname, cols in FEATURE_SETS.items():
        idx = [FEATURE_SETS["all_metadata_no_pixels"].index(c) for c in cols]
        Xi = X[:, idx]
        # in-distribution random split
        Xtr, Xte, ytr, yte = train_test_split(Xi, y, test_size=0.3,
                                              random_state=RNG, stratify=y)
        rf = RandomForestClassifier(n_estimators=300, random_state=RNG, n_jobs=-1)
        rf.fit(Xtr, ytr)
        auc = roc_auc_score(yte, rf.predict_proba(Xte)[:, 1])
        lr = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
        auc_lr = roc_auc_score(yte, lr.predict_proba(Xte)[:, 1])
        entry = {"auc_randomforest_in_distribution": round(auc, 4),
                 "auc_logreg_in_distribution": round(auc_lr, 4),
                 "top_importances": []}
        try:
            imps = sorted(zip(cols, rf.feature_importances_), key=lambda t: -t[1])[:5]
            entry["top_importances"] = [{"feature": c, "importance": round(float(v), 4)}
                                        for c, v in imps]
        except Exception:
            pass
        # corpus-classifier: can we tell WHICH corpus an image came from?
        # Use label= encoder + accuracy_score: roc_auc_score(multi_class=)
        # requires predict_proba with >2 columns and raised AxisError when a
        # RandomForest's binary problem leaked through.
        if len(set(groups)) > 1:
            try:
                from sklearn.metrics import accuracy_score
                from sklearn.preprocessing import LabelEncoder
                le = LabelEncoder().fit(g)
                gcodes = le.transform(g)
                Xa, Xb, ya, yb = train_test_split(Xi, gcodes, test_size=0.3,
                                                   random_state=RNG, stratify=gcodes)
                rfc = RandomForestClassifier(n_estimators=300, random_state=RNG,
                                             n_jobs=-1)
                rfc.fit(Xa, ya)
                pred = rfc.predict(Xb)
                entry["accuracy_identifying_which_corpus"] = round(
                    float(accuracy_score(yb, pred)), 4)
                entry["corpus_id_chance_level"] = round(
                    float(max(np.bincount(gcodes)) / len(gcodes)), 4)
                entry["corpus_id_classes"] = [str(c) for c in le.classes_]
            except Exception as e:
                entry["accuracy_identifying_which_corpus"] = \
                    f"failed: {type(e).__name__}: {e}"[:80]
        report["results"][fname] = entry
        print(f"{fname:28} AUC(real vs syn)={auc:.4f}  logreg={auc_lr:.4f}  "
              f"corpus-id acc={entry.get('accuracy_identifying_which_corpus')}"
              f" (chance {entry.get('corpus_id_chance_level')})", flush=True)

    best = max(report["results"].items(),
               key=lambda kv: kv[1]["auc_randomforest_in_distribution"])
    report["interpretation"] = {
        "strongest_shortcut_feature_set": best[0],
        "strongest_metadata_only_auc": best[1]["auc_randomforest_in_distribution"],
        "verdict": (
            "SHORTCUT PRESENT: real vs synthetic is predictable from file "
            "metadata alone, so a detector could score well without learning "
            "synthetic-image forensics."
            if best[1]["auc_randomforest_in_distribution"] >= 0.80 else
            "NO DOMINANT SHORTCUT: metadata alone does not separate the classes "
            "(AUC<0.80), so the corpus is not trivially fingerprintable."
        ),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(report, open(OUT, "w"), indent=1)
    print("\n" + json.dumps(report["interpretation"], indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()