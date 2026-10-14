"""
Conditional error analysis for the A/B detector pair.

The question this answers is narrow and decisive: if the two detectors
agree, how often are they wrong together, and if they disagree, how
often is the disagreement doing real work? Abstention is only justified
if the second number is materially better than guessing.

Reuses the cached evaluation artefacts so nothing is recomputed.
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
from scripts.run_phase37_detector_b import (  # noqa: E402
    BACKBONE, DEVICE, abs_path_for, labels_from_paths, roc_auc,
)

OUT = ROOT / "results" / "phase37"


def main() -> None:
    splits = json.loads((ROOT / "results/phase3/splits.json").read_text(encoding="utf-8"))
    split = splits["splits"]["C_clean_CF_generator_holdout"]
    test_rel = split["test"]
    test_paths = [abs_path_for(p) for p in test_rel]
    y = labels_from_paths(test_rel)

    store = db.load_probe(ROOT / "models" / "detector_b_clip_probe.joblib")
    emb = db.embed_images(test_paths, BACKBONE, device=DEVICE)
    p_b = store["classifier"].predict_proba(store["scaler"].transform(emb))[:, 1]

    from PIL import Image
    from app.image.preprocessing import to_normalized_array, resize_long_edge, center_crop
    from app.image.model_loader import load_image_model
    model, _ = load_image_model()
    p_a = np.asarray([
        float(model.predict(to_normalized_array(
            center_crop(resize_long_edge(Image.open(p).convert("RGB"), 518), 518)[0])))
        for p in test_paths
    ])

    a_bin = (p_a >= 0.5).astype(int)
    b_bin = (p_b >= 0.5).astype(int)
    agree = a_bin == b_bin
    ood = np.array([
        db.distribution_status(db.knn_distance_score(e, store), s := store) == "out_of_distribution"
        for e in emb
    ])

    def block(mask, label):
        n = int(mask.sum())
        if n == 0:
            return {"n": 0}
        # "wrong" = the pair's binary verdict differs from ground truth
        wrong = int((a_bin[mask] != y[mask]).sum())
        wrong_b = int((b_bin[mask] != y[mask]).sum())
        synth = int((y[mask] == 1).sum())
        # the dangerous error: synthetic image presented as real
        fa = int(((y[mask] == 1) & (a_bin[mask] == 0)).sum())
        fb = int(((y[mask] == 1) & (b_bin[mask] == 0)).sum())
        return {
            "n": n,
            "share": round(n / len(y), 4),
            "detector_a_error_rate": round(wrong / n, 4),
            "detector_b_error_rate": round(wrong_b / n, 4),
            "synthetic_in_block": synth,
            "false_authentic_A": fa,
            "false_authentic_B": fb,
        }

    res = {
        "n_total": len(y),
        "when_agree": block(agree, "agree"),
        "when_disagree": block(~agree, "disagree"),
        "ood_n": int(ood.sum()),
        "ood_and_disagree": int((ood & ~agree).sum()),
    }

    # Abstention policy, swept. Report the trade-off honestly rather than
    # picking one operating point and presenting it as the only option.
    sweep = []
    for use_conflict, use_ood in [(False, False), (True, False), (False, True), (True, True)]:
        mask = np.zeros(len(y), bool)
        if use_conflict:
            mask |= ~agree
        if use_ood:
            mask |= ood
        answered = ~mask
        if answered.sum() == 0:
            continue
        avg = ((p_a[answered] + p_b[answered]) / 2 >= 0.5).astype(int)
        sy = y[answered]
        fa = int(((sy == 1) & (avg == 0)).sum())
        tot_synth = int((sy == 1).sum())
        sweep.append({
            "abstain_on_conflict": use_conflict,
            "abstain_on_ood": use_ood,
            "coverage": round(float(answered.mean()), 4),
            "accuracy_on_answered": round(float((avg == sy).mean()), 4),
            "false_authentic_rate_on_answered": round(fa / max(tot_synth, 1), 4),
            "false_authentic_absolute": fa,
        })
    res["abstention_sweep"] = sweep

    # Correlation check the brief explicitly warns about.
    res["independence"] = {
        "pearson_r": round(float(np.corrcoef(p_a, p_b)[0, 1]), 4),
        "spearman_r": round(float(np.corrcoef(
            np.argsort(np.argsort(p_a)), np.argsort(np.argsort(p_b)))[0, 1]), 4),
        "identical_predictions": int((a_bin == b_bin).sum()),
        "note": "Low correlation means the pair is not redundant; "
                "high correlation would mean 'agreement' is an artefact.",
    }

    (OUT / "ensemble_agreement_analysis.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
