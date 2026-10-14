"""
Robustness, calibration and uncertainty policy for the temporary winner.

Run against a candidate chosen on C_clean. Robustness here is what
distinguishes a detector that works on the images it was trained on from
one that has learned a fragile fingerprint.

Three families of perturbation:

JPEG recompression (95/85/70/50)
    The most important single test. A detector keyed on compression
    artefacts collapses the moment a platform recompresses an image, which
    every social platform does.

Resolution (512/256/128)
    Confidence that tracks resolution is a detector that has learned file
    geometry rather than content.

Mild blur / sharpen
    Sanity check that predictions are not knife-edge sensitive.

Calibration
-----------
Temperature scaling fitted on the VALIDATION split only. Never on test:
fitting a calibrator on the data you then report is a silent way to
manufacture a better number.

Uncertainty policy
------------------
Three-way thresholds tuned on validation. The middle band is named
UNCERTAIN rather than being forced into a binary call - a detector that
must answer yes/no will guess in exactly the region where it knows least.
"""

from __future__ import annotations

import csv
import io
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageFilter
from sklearn.metrics import brier_score_loss, f1_score, roc_auc_score
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
RESULTS = BACKEND / "results" / "phase3"
MODELS_DIR = BACKEND / "models"
SPLITS = RESULTS / "splits.json"

SEED = 42
IMAGE_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
TO_TENSOR = transforms.Compose([transforms.ToTensor(), transforms.Normalize(MEAN, STD)])

INTERPRETATION = (
    "109 held-out generator variants, predominantly LatDiff (99.3% of the "
    "synthetic corpus). Cross-family generalisation is NOT established."
)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - m), min(1.0, c + m)


def label_of(rel: str) -> int:
    return 1 if "/synthetic/" in rel.replace("\\", "/") else 0


class PerturbedDataset(Dataset):
    """Applies the same perturbation to every image in the set."""

    def __init__(self, paths, transform, *, jpeg=None, long_edge=None,
                 blur=None, sharpen=False):
        self.paths, self.transform = paths, transform
        self.jpeg, self.long_edge, self.blur, self.sharpen = jpeg, long_edge, blur, sharpen

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        try:
            with Image.open(PROJECT / self.paths[index]) as handle:
                image = handle.convert("RGB")
        except Exception:  # noqa: BLE001
            image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))

        if self.long_edge:
            w, h = image.size
            if max(w, h) > self.long_edge:
                ratio = self.long_edge / max(w, h)
                image = image.resize((max(1, int(w * ratio)), max(1, int(h * ratio))),
                                     Image.BILINEAR)
        if self.blur:
            image = image.filter(ImageFilter.GaussianBlur(radius=self.blur))
        if self.sharpen:
            image = image.filter(ImageFilter.SHARPEN)
        if self.jpeg:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=self.jpeg)
            buffer.seek(0)
            with Image.open(buffer) as reopened:
                image = reopened.convert("RGB")

        return self.transform(image.resize((IMAGE_SIZE, IMAGE_SIZE)))


def load_model(architecture: str) -> nn.Module:
    if architecture == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    else:
        model = models.vit_b_16(weights=None)
        model.heads.head = nn.Linear(model.heads.head.in_features, 2)
    checkpoint = torch.load(MODELS_DIR / f"basirah-image-cand-{architecture}.pt",
                            map_location=DEVICE, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    return model.to(DEVICE).eval()


def predict(model, paths, **kwargs) -> np.ndarray:
    loader = DataLoader(PerturbedDataset(paths, TO_TENSOR, **kwargs),
                        batch_size=64, num_workers=4)
    out = []
    with torch.no_grad():
        for images in loader:
            out.extend(torch.softmax(model(images.to(DEVICE)), 1)[:, 1].cpu().numpy().tolist())
    return np.asarray(out)


def ece(probs: np.ndarray, labels: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error with equal-width bins."""
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for i in range(bins):
        mask = (probs >= edges[i]) & (probs < edges[i + 1] if i < bins - 1 else probs <= 1.0)
        if not mask.any():
            continue
        total += mask.mean() * abs(probs[mask].mean() - labels[mask].mean())
    return float(total)


def main() -> int:
    architecture = sys.argv[1] if len(sys.argv) > 1 else "efficientnet_b0"
    clean = json.loads(SPLITS.read_text(encoding="utf-8"))["splits"]["C_clean_CF_generator_holdout"]
    test_paths, test_labels = list(clean["test"]), None
    test_labels = np.asarray([label_of(p) for p in test_paths])
    val_paths = list(clean.get("val") or [])
    val_labels = np.asarray([label_of(p) for p in val_paths])

    model = load_model(architecture)
    print(f"robustness for: {architecture}")
    print(f"  {INTERPRETATION}")

    baseline = predict(model, test_paths)
    base_auc = roc_auc_score(test_labels, baseline)
    base_fpr = float(((baseline >= 0.5) & (test_labels == 0)).sum()) / max(int((test_labels == 0).sum()), 1)
    print(f"  baseline auc={base_auc:.4f} fpr={base_fpr:.4f}")

    # ---- JPEG robustness -------------------------------------------
    print()
    print("=== JPEG recompression ===")
    jpeg_rows = []
    for quality in (95, 85, 70, 50):
        probs = predict(model, test_paths, jpeg=quality)
        preds = probs >= 0.5
        fp = int((preds & (test_labels == 0)).sum())
        n_real = int((test_labels == 0).sum())
        row = {
            "quality": quality,
            "roc_auc": round(float(roc_auc_score(test_labels, probs)), 4),
            "f1": round(float(f1_score(test_labels, preds, zero_division=0)), 4),
            "mean_prob_shift": round(float(np.abs(probs - baseline).mean()), 4),
            "synthetic_recall": round(float(preds[test_labels == 1].mean()), 4),
            "real_fpr": round(fp / max(n_real, 1), 4),
            "real_fpr_ci95": [round(v, 4) for v in wilson(fp, n_real)],
            "decision_flips": int(((preds) != (baseline >= 0.5)).sum()),
        }
        jpeg_rows.append(row)
        print(f"  q={quality:3}  auc={row['roc_auc']:.4f} f1={row['f1']:.4f} "
              f"shift={row['mean_prob_shift']:.4f} fpr={row['real_fpr']:.4f} "
              f"flips={row['decision_flips']}")

    # ---- resolution robustness -------------------------------------
    print()
    print("=== resolution ===")
    res_rows = []
    for edge in (512, 256, 128):
        probs = predict(model, test_paths, long_edge=edge)
        preds = probs >= 0.5
        fp = int((preds & (test_labels == 0)).sum())
        n_real = int((test_labels == 0).sum())
        row = {
            "long_edge": edge,
            "roc_auc": round(float(roc_auc_score(test_labels, probs)), 4),
            "f1": round(float(f1_score(test_labels, preds, zero_division=0)), 4),
            "mean_prob_shift": round(float(np.abs(probs - baseline).mean()), 4),
            "real_fpr": round(fp / max(n_real, 1), 4),
            "real_fpr_ci95": [round(v, 4) for v in wilson(fp, n_real)],
        }
        res_rows.append(row)
        print(f"  {edge:4}px auc={row['roc_auc']:.4f} f1={row['f1']:.4f} "
              f"shift={row['mean_prob_shift']:.4f} fpr={row['real_fpr']:.4f}")

    # ---- mild blur / sharpen ---------------------------------------
    print()
    print("=== mild perturbation ===")
    misc_rows = []
    for label, kwargs in (("blur_r1.0", {"blur": 1.0}), ("sharpen", {"sharpen": True})):
        probs = predict(model, test_paths, **kwargs)
        row = {
            "perturbation": label,
            "roc_auc": round(float(roc_auc_score(test_labels, probs)), 4),
            "mean_prob_shift": round(float(np.abs(probs - baseline).mean()), 4),
        }
        misc_rows.append(row)
        print(f"  {label:10} auc={row['roc_auc']:.4f} shift={row['mean_prob_shift']:.4f}")

    # ---- calibration ------------------------------------------------
    print()
    print("=== calibration (temperature scaling fitted on VALIDATION) ===")
    val_probs = predict(model, val_paths) if val_paths else None
    best_T, best_brier = 1.0, float(brier_score_loss(test_labels, baseline))
    if val_probs is not None and len(set(val_labels.tolist())) > 1:
        grid = np.concatenate([np.linspace(0.5, 3.0, 51)])
        for temperature in grid:
            scaled = 1.0 / (1.0 + np.exp(-np.log(np.clip(val_probs, 1e-6, 1 - 1e-6)
                                                  / np.clip(val_probs, 1e-6, 1 - 1e-6))
                                            / temperature))
            score = brier_score_loss(val_labels, scaled)
            if score < best_brier:
                best_brier, best_T = score, float(temperature)
        print(f"  selected temperature: {best_T:.2f} (chosen on validation Brier)")
    else:
        print("  no validation split; raw probabilities retained")

    if best_T != 1.0:
        logits = np.log(np.clip(baseline, 1e-6, 1 - 1e-6) /
                        np.clip(1 - baseline, 1e-6, 1 - 1e-6))
        calibrated = 1.0 / (1.0 + np.exp(-logits / best_T))
    else:
        calibrated = baseline

    calibration_rows = [
        {"method": "raw", "brier": round(float(brier_score_loss(test_labels, baseline)), 5),
         "ece": round(ece(baseline, test_labels), 5), "temperature": 1.0},
        {"method": f"temperature_T{best_T:.2f}",
         "brier": round(float(brier_score_loss(test_labels, calibrated)), 5),
         "ece": round(ece(calibrated, test_labels), 5), "temperature": best_T},
    ]
    for row in calibration_rows:
        print(f"  {row['method']:22} brier={row['brier']:.5f} ece={row['ece']:.5f}")

    # ---- uncertainty thresholds from validation --------------------
    print()
    print("=== uncertainty policy (thresholds tuned on VALIDATION) ===")
    if val_probs is not None:
        target_fpr = 0.05
        negatives = np.sort(val_probs[val_labels == 0])[::-1]
        index = min(int(target_fpr * len(negatives)), len(negatives) - 1)
        upper = float(negatives[index]) if len(negatives) else 0.5
        lower = float(1.0 - upper)
    else:
        upper, lower = 0.9, 0.1
    print(f"  LIKELY_REAL      p <= {lower:.4f}")
    print(f"  UNCERTAIN        {lower:.4f} < p < {upper:.4f}")
    print(f"  LIKELY_SYNTHETIC p >= {upper:.4f}")
    print(f"  (upper bound set at {target_fpr:.0%} validation FPR on real images)")

    fraction_uncertain = float(((baseline > lower) & (baseline < upper)).mean())
    print(f"  test images in UNCERTAIN band: {fraction_uncertain:.1%}")

    # ---- persist ----------------------------------------------------
    def write(name, rows):
        if not rows:
            return
        path = RESULTS / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"  written: {path}")

    print()
    write("jpeg_robustness.csv", jpeg_rows)
    write("resolution_robustness.csv", res_rows)
    write("calibration_results.csv", calibration_rows)

    summary = [
        {"check": "baseline_roc_auc", "value": round(base_auc, 4)},
        {"check": "jpeg_q50_roc_auc", "value": jpeg_rows[-1]["roc_auc"]},
        {"check": "jpeg_auc_drop_q50", "value": round(base_auc - jpeg_rows[-1]["roc_auc"], 4)},
        {"check": "resolution_128_roc_auc", "value": res_rows[-1]["roc_auc"]},
        {"check": "resolution_auc_drop_128", "value": round(base_auc - res_rows[-1]["roc_auc"], 4)},
        {"check": "brier_raw", "value": calibration_rows[0]["brier"]},
        {"check": "brier_calibrated", "value": calibration_rows[-1]["brier"]},
        {"check": "temperature", "value": best_T},
        {"check": "uncertainty_lower", "value": round(lower, 4)},
        {"check": "uncertainty_upper", "value": round(upper, 4)},
        {"check": "uncertain_fraction_on_test", "value": round(fraction_uncertain, 4)},
        {"check": "held_out_interpretation", "value": INTERPRETATION},
    ]
    write("robustness_summary.csv", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())