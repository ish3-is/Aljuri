"""
Train and evaluate Detector B, then test the assumption the whole
ensemble rests on: that a second detector on an independent
representation is actually worth having.

The interesting output is NOT Detector B's standalone accuracy. It is the
agreement/disagreement breakdown against Detector A, because two
detectors that merely duplicate each other would manufacture false
confidence. Agreement is only evidence if the two can genuinely differ.

Split C_clean_CF_generator_holdout is used deliberately: it holds out
109 generators, so Detector B is measured on generators it never saw
during fitting. That is the closest available proxy for the real world.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.image.ensemble import detector_b as db  # noqa: E402

SPLITS = ROOT / "results" / "phase3" / "splits.json"
OUT_DIR = ROOT / "results" / "phase37"
CKPT_DIR = ROOT / "models"

BACKBONE = "vit_base_patch16_clip_224.openai"


def _device() -> str:
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


DEVICE = _device()


def labels_from_paths(paths: list[str]) -> np.ndarray:
    """0 = real, 1 = synthetic. Path is the only label source."""
    y = []
    for p in paths:
        pl = p.replace("\\", "/").lower()
        if "/synthetic/" in pl:
            y.append(1)
        elif "/real/" in pl:
            y.append(0)
        else:
            raise ValueError(f"cannot infer label from {p}")
    return np.asarray(y, dtype=np.int8)


def roc_auc(y: np.ndarray, p: np.ndarray) -> float:
    order = np.argsort(p)
    ranks = np.empty(len(p), dtype=float)
    ranks[order] = np.arange(1, len(p) + 1)
    # average ranks for ties
    sorted_p = p[order]
    i = 0
    while i < len(sorted_p):
        j = i
        while j + 1 < len(sorted_p) and sorted_p[j + 1] == sorted_p[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = ranks[order[i:j + 1]].mean()
        i = j + 1
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def abs_path_for(rel: str) -> str:
    """
    splits.json stores paths with a `backend/` prefix, but ROOT is
    already the backend directory, so that prefix must be stripped
    before joining. Try the plausible roots rather than guessing
    one, and prefer whichever actually exists.
    """
    norm = rel.replace("\\", "/")
    candidates = [
        ROOT / norm,
        ROOT / norm.removeprefix("backend/"),
        ROOT.parent / norm,
        Path(norm),
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    # Return the most plausible path so the caller can report it.
    return str(candidates[1])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)

    splits = json.loads(SPLITS.read_text(encoding="utf-8"))["splits"]
    split = splits["C_clean_CF_generator_holdout"]
    train_rel = split["train"]
    test_rel = split["test"]

    train_paths = [abs_path_for(p) for p in train_rel]
    test_paths = [abs_path_for(p) for p in test_rel]
    missing = [p for p in train_paths + test_paths if not Path(p).exists()]
    if missing:
        print(f"WARNING: {len(missing)} missing image(s); first = {missing[0]}")

    y_train = labels_from_paths(train_rel)
    y_test = labels_from_paths(test_rel)
    print(f"train n={len(train_paths)} synthetic_rate={y_train.mean():.3f}")
    print(f"test  n={len(test_paths)} synthetic_rate={y_test.mean():.3f}")
    print(f"device={DEVICE} backbone={BACKBONE}")

    t0 = time.time()
    print("embedding train ...")
    e_train = db.embed_images(train_paths, BACKBONE, device=DEVICE, progress_every=400)
    print(f"  {e_train.shape} in {time.time() - t0:.1f}s")

    t0 = time.time()
    print("embedding test ...")
    e_test = db.embed_images(test_paths, BACKBONE, device=DEVICE, progress_every=400)
    print(f"  {e_test.shape} in {time.time() - t0:.1f}s")

    store = db.fit_probe(e_train, y_train)
    db.save_probe(store, CKPT_DIR / "detector_b_clip_probe.joblib")

    results: dict = {
        "backbone": BACKBONE,
        "device": DEVICE,
        "embedding_dim": int(e_train.shape[1]),
        "train_n": len(train_paths),
        "test_n": len(test_paths),
        "train_synthetic_rate": float(y_train.mean()),
        "test_synthetic_rate": float(y_test.mean()),
    }

    # ---- Detector B standalone ----
    p_test = store["classifier"].predict_proba(store["scaler"].transform(e_test))[:, 1]
    auc = roc_auc(y_test, p_test)
    thr = 0.5
    pred = (p_test >= thr).astype(int)
    tp = int(((pred == 1) & (y_test == 1)).sum())
    tn = int(((pred == 0) & (y_test == 0)).sum())
    fp = int(((pred == 1) & (y_test == 0)).sum())
    fn = int(((pred == 0) & (y_test == 1)).sum())
    results["detector_b"] = {
        "roc_auc": round(auc, 4),
        "threshold": thr,
        "balanced_accuracy": round(0.5 * (tp / max(tp + fn, 1) + tn / max(tn + fp, 1)), 4),
        "fpr": round(fp / max(fp + tn, 1), 4),
        "fnr": round(fn / max(fn + tp, 1), 4),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "false_authentic_rate": round(fn / max(fn + tp, 1), 4),
    }
    print(f"\nDetector B: AUC={auc:.4f} bal_acc={results['detector_b']['balanced_accuracy']}")

    # ---- OOD distribution on test ----
    dist_counts = {"in_distribution": 0, "borderline": 0, "out_of_distribution": 0}
    ood_scores = []
    for emb in e_test:
        s = db.knn_distance_score(emb, store)
        d = db.distribution_status(s, store)
        dist_counts[d] += 1
        ood_scores.append(s)
    results["ood"] = {
        "counts": dist_counts,
        "score_mean": round(float(np.mean(ood_scores)), 4),
        "score_p95": round(float(np.percentile(ood_scores, 95)), 4),
        "thresholds": {
            "nn_sim_mean": round(store["nn_sim_mean"], 4),
            "nn_sim_std": round(store["nn_sim_std"], 4),
            "nn_sim_p05": round(store["nn_sim_p05"], 4),
        },
    }
    print(f"OOD on test: {dist_counts}")

    # ---- Detector A, for the agreement analysis ----
    a_scores = None
    try:
        from pathlib import Path as _P
        from PIL import Image as _Image
        from app.image.preprocessing import to_normalized_array, resize_long_edge, center_crop
        from app.image.model_loader import load_image_model

        model, _note = load_image_model()
        if model is not None:
            # Detector A is fed through the SAME production preprocessing
            # contract the API uses, so the comparison is against the
            # behaviour actually shipped rather than a notebook shortcut.
            a_scores = []
            t0 = time.time()
            for p in test_paths:
                with _Image.open(p) as im:
                    im = im.convert("RGB")
                    im, _cropped = center_crop(resize_long_edge(im, 518), 518)
                    tensor = to_normalized_array(im)
                a_scores.append(float(model.predict(tensor)))
            a_scores = np.asarray(a_scores)
            results["detector_a"] = {"roc_auc": round(roc_auc(y_test, a_scores), 4),
                                     "secs": round(time.time() - t0, 1)}
            print(f"Detector A: AUC={results['detector_a']['roc_auc']}")
        else:
            print("Detector A unavailable:", _note)
    except Exception as exc:  # noqa: BLE001
        print(f"Detector A could not be scored: {type(exc).__name__}: {exc}")

    # ---- The question that matters: do they actually differ? ----
    if a_scores is not None:
        a_bin = (a_scores >= 0.5).astype(int)
        b_bin = (p_test >= 0.5).astype(int)
        agree = a_bin == b_bin
        agree_strong = (np.abs(a_scores - 0.5) >= 0.3) & (np.abs(p_test - 0.5) >= 0.3)

        conflict = ~agree
        # Of the disagreements, how many are on the dangerous side:
        # synthetic image that one detector called confident-real?
        synth = y_test == 1
        false_authentic_a = int((synth & (a_scores < 0.5)).sum())
        false_authentic_b = int((synth & (p_test < 0.5)).sum())
        false_authentic_either = int((synth & ((a_scores < 0.5) | (p_test < 0.5))).sum())
        false_authentic_both = int((synth & (a_scores < 0.5) & (p_test < 0.5)).sum())

        results["agreement"] = {
            "agreement_rate": round(float(agree.mean()), 4),
            "conflict_rate": round(float(conflict.mean()), 4),
            "strong_agreement_n": int(agree_strong.sum()),
            "strong_agreement_rate": round(float(agree_strong.mean()), 4),
            "disagreement_n": int(conflict.sum()),
            "false_authentic_detector_a": false_authentic_a,
            "false_authentic_detector_b": false_authentic_b,
            "false_authentic_either_detector": false_authentic_either,
            "false_authentic_both_detectors": false_authentic_both,
            "synthetic_total": int(synth.sum()),
            "pearson_r": round(float(np.corrcoef(a_scores, p_test)[0, 1]), 4),
        }
        # Abstention: conflict OR out-of-distribution.
        ood_flag = np.array(
            [db.distribution_status(db.knn_distance_score(e, store), store) == "out_of_distribution"
             for e in e_test]
        )
        abstain = conflict | ood_flag
        answered = ~abstain
        if answered.sum():
            sub_p = ((a_scores[answered] + p_test[answered]) / 2 >= 0.5).astype(int)
            sy = y_test[answered]
            atp = int(((sub_p == 1) & (sy == 1)).sum())
            afn = int(((sub_p == 0) & (sy == 1)).sum())
            results["ensemble_with_abstention"] = {
                "abstention_rate": round(float(abstain.mean()), 4),
                "coverage": round(float(answered.mean()), 4),
                "accuracy_on_answered": round(float((sub_p == sy).mean()), 4),
                "false_authentic_rate_on_answered": round(afn / max(atp + afn, 1), 4),
                "answered_n": int(answered.sum()),
            }
        print(f"\nAGREEMENT: rate={results['agreement']['agreement_rate']} "
              f"r={results['agreement']['pearson_r']}")
        print(f"FALSE AUTHENTIC  A={false_authentic_a}  B={false_authentic_b}  "
              f"either={false_authentic_either}  both={false_authentic_both}  "
              f"of {int(synth.sum())} synthetic")

    (OUT_DIR / "detector_b_eval.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT_DIR / 'detector_b_eval.json'}")


if __name__ == "__main__":
    main()
