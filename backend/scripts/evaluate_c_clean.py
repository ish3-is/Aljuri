"""
Step 1 evaluation: rigorous comparison on Split C_clean only.

Deliberately NOT compared here: the old A/B/C splits. Those were
source-confounded (source-only AUC 0.9409) and are evidence of dataset
contamination, not of synthetic-detection performance.

Language control
----------------
This module never writes "109 unseen generators". The holdout is 109
*generator variants*, and 99.3% of the synthetic corpus is LatDiff, so
the held-out set is overwhelmingly LatDiff fine-tunes. Cross-FAMILY
generalisation is not established by this split, and the reports say so.

Confidence intervals
--------------------
Every rate is reported with a Wilson 95% interval. A measured 0% false
positive rate on 100 images is not "zero" - it is somewhere in roughly
[0, 3.7%], and reporting the bare 0 would overstate what 100 images can
show.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader
from torchvision import models, transforms

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
RESULTS = BACKEND / "results" / "phase3"
MODELS_DIR = BACKEND / "models"
SPLITS = RESULTS / "splits.json"
PROGRESS = RESULTS / "training_progress.json"
CONF_DIR = RESULTS / "c_clean_confusion_matrices"

SEED = 42
IMAGE_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

INTERPRETATION = (
    "109 held-out generator variants, predominantly LatDiff. The synthetic "
    "corpus is 99.3% LatDiff (2184/2200); GAN=8, PixDiff=4, Other=4. This "
    "split does NOT establish cross-family generalisation."
)


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float, float]:
    if total == 0:
        return 0.0, 0.0, 1.0
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return p, max(0.0, centre - margin), min(1.0, centre + margin)


def label_of(relative: str) -> int:
    return 1 if "/synthetic/" in relative.replace("\\", "/") else 0


class ListDataset(torch.utils.data.Dataset):
    def __init__(self, paths, transform):
        self.paths, self.transform = paths, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        try:
            with Image.open(PROJECT / self.paths[index]) as handle:
                image = handle.convert("RGB")
        except Exception:  # noqa: BLE001
            image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))
        return self.transform(image)


EVAL_TRANSFORM = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


def load_cnn(architecture: str) -> nn.Module:
    if architecture == "efficientnet_b0":
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    else:
        model = models.vit_b_16(weights=None)
        model.heads.head = nn.Linear(model.heads.head.in_features, 2)
    checkpoint = torch.load(
        MODELS_DIR / f"basirah-image-cand-{architecture}.pt",
        map_location=DEVICE, weights_only=False,
    )
    model.load_state_dict(checkpoint["state_dict"])
    return model.to(DEVICE).eval()


def predict(model, paths, batch_size: int = 64) -> np.ndarray:
    loader = DataLoader(ListDataset(paths, EVAL_TRANSFORM),
                        batch_size=batch_size, num_workers=0)
    out = []
    with torch.no_grad():
        for images in loader:
            logits = model(images.to(DEVICE))
            out.extend(torch.softmax(logits, 1)[:, 1].cpu().numpy().tolist())
    return np.asarray(out)


def latency_ms(model, paths, repeats: int = 3) -> float:
    """Median wall-clock for a full pass over the test set, per image."""
    loader = DataLoader(ListDataset(paths, EVAL_TRANSFORM), batch_size=32, num_workers=0)
    timings = []
    for _ in range(repeats):
        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.no_grad():
            for images in loader:
                model(images.to(DEVICE))
        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
        timings.append((time.perf_counter() - started) / len(paths) * 1000)
    return round(float(np.median(timings)), 3)


def model_size_mb(path: Path) -> float:
    return round(path.stat().st_size / 1e6, 2) if path.exists() else 0.0


def full_metrics(probs: np.ndarray, labels: np.ndarray, name: str) -> dict:
    preds = (probs >= 0.5).astype(int)
    n_real = int((labels == 0).sum())
    n_syn = int((labels == 1).sum())
    tp = int(((preds == 1) & (labels == 1)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())

    fpr, fpr_lo, fpr_hi = wilson(fp, n_real)
    recall, rec_lo, rec_hi = wilson(tp, n_syn)
    precision, prec_lo, prec_hi = wilson(tp, tp + fp)

    return {
        "model": name,
        "n_test": int(len(labels)),
        "n_real": n_real,
        "n_synthetic": n_syn,
        "roc_auc": round(float(roc_auc_score(labels, probs)), 4),
        "pr_auc": round(float(average_precision_score(labels, probs)), 4),
        "accuracy": round(float(accuracy_score(labels, preds)), 4),
        "f1": round(float(f1_score(labels, preds, zero_division=0)), 4),
        "precision": round(precision, 4),
        "precision_ci95": [round(prec_lo, 4), round(prec_hi, 4)],
        "recall": round(recall, 4),
        "recall_ci95": [round(rec_lo, 4), round(rec_hi, 4)],
        "fpr": round(fpr, 4),
        "fpr_ci95": [round(fpr_lo, 4), round(fpr_hi, 4)],
        "fnr": round(fn / max(n_syn, 1), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, preds)), 4),
        "brier": round(float(brier_score_loss(labels, probs)), 4),
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "true_negatives": n_real - fp,
    }


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    CONF_DIR.mkdir(parents=True, exist_ok=True)

    clean = json.loads(SPLITS.read_text(encoding="utf-8"))["splits"]["C_clean_CF_generator_holdout"]
    test_paths = list(clean["test"])
    test_labels = np.asarray([label_of(p) for p in test_paths])
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))

    print(f"Split C_clean only. {INTERPRETATION}")
    print(f"test: {len(test_paths):,} images "
          f"({int((test_labels == 0).sum())} real, {int((test_labels == 1).sum())} synthetic)")
    print(f"stages available: {list(progress['stages'].keys())}")
    print()

    rows: list[dict] = []

    for stage_name, entry in progress["stages"].items():
        architecture = entry.get("architecture", stage_name)
        print(f"--- {stage_name} ({architecture}) ---")

        if stage_name in ("efficientnet_done", "vit_done"):
            key = "efficientnet_b0" if stage_name == "efficientnet_done" else "vit_b_16"
            path = MODELS_DIR / f"basirah-image-cand-{key}.pt"
            if not path.exists():
                print(f"    weights missing: {path.name}, skipping")
                continue
            model = load_cnn(key)
            probs = predict(model, test_paths)
            latency = latency_ms(model, test_paths)
            size = model_size_mb(path)
        elif stage_name == "embedding_done":
            import joblib

            path = MODELS_DIR / "basirah-image-cand-dinov2_lr.joblib"
            if not path.exists():
                print(f"    embedding artifact missing, skipping")
                continue
            import timm

            backbone_name = entry.get("feature_backbone", "vit_small_patch14_dinov2")
            backbone = timm.create_model(backbone_name, pretrained=True, num_classes=0)
            backbone = backbone.to(DEVICE).eval()

            def embed(paths):
                loader = DataLoader(ListDataset(paths, EVAL_TRANSFORM),
                                    batch_size=64, num_workers=0)
                out = []
                with torch.no_grad():
                    for images in loader:
                        features = backbone(images.to(DEVICE))
                        if features.ndim == 3:
                            features = features.mean(dim=1)
                        out.append(features.cpu().numpy())
                return np.concatenate(out, axis=0)

            classifier = joblib.load(path)
            probs = classifier.predict_proba(embed(test_paths))[:, 1]
            latency = latency_ms(backbone, test_paths)
            size = model_size_mb(path)
        else:
            continue

        row = full_metrics(probs, test_labels, stage_name)
        row["architecture"] = architecture
        row["inference_latency_ms_per_image"] = latency
        row["model_size_mb"] = size
        row["held_out_interpretation"] = INTERPRETATION
        rows.append(row)
        print(f"    auc={row['roc_auc']} pr_auc={row['pr_auc']} f1={row['f1']} "
              f"fpr={row['fpr']} ci={row['fpr_ci95']} brier={row['brier']}")
        print(f"    latency={latency} ms/image  size={size} MB")

        # Confusion matrix
        matrix = confusion_matrix(test_labels, (probs >= 0.5).astype(int), labels=[0, 1])
        np.savetxt(CONF_DIR / f"{stage_name}_confusion.txt", matrix, fmt="%d")
        np.save(RESULTS / f"_probs_{stage_name}.npy", probs)

    if not rows:
        print("no completed stages to evaluate")
        return 1

    # ---- write CSVs -------------------------------------------------
    fields = list(rows[0].keys())
    with (RESULTS / "c_clean_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    comparison_fields = [
        "model", "architecture", "roc_auc", "pr_auc", "f1", "precision",
        "precision_ci95", "recall", "recall_ci95", "fpr", "fpr_ci95", "fnr",
        "balanced_accuracy", "brier", "inference_latency_ms_per_image", "model_size_mb",
    ]
    with (RESULTS / "c_clean_model_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=comparison_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # ---- ROC / PR figures ------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, 2, figsize=(11, 4.4))
        for row in rows:
            probs = np.load(RESULTS / f"_probs_{row['model']}.npy")
            for axis, metric in zip(axes, ("roc", "pr")):
                if metric == "roc":
                    fpr, tpr, _ = __import__("sklearn.metrics", fromlist=["x"]).roc_curve(
                        test_labels, probs)
                    axis.plot(fpr, tpr, label=f"{row['model']} (AUC {row['roc_auc']:.4f})")
                    axis.set_xlabel("False positive rate")
                    axis.set_ylabel("True positive rate")
                    axis.set_title("ROC — Split C_clean")
                else:
                    precision, recall, _ = __import__(
                        "sklearn.metrics", fromlist=["x"]).precision_recall_curve(
                        test_labels, probs)
                    axis.plot(recall, precision, label=f"{row['model']} (PR {row['pr_auc']:.4f})")
                    axis.set_xlabel("Recall")
                    axis.set_ylabel("Precision")
                    axis.set_title("Precision-Recall — Split C_clean")
            axes[0].plot([0, 1], [0, 1], "k--", alpha=0.3)
        for axis in axes:
            axis.legend(fontsize=8)
            axis.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(RESULTS / "c_clean_roc_pr.png", dpi=130)
        print(f"\nwritten: {RESULTS / 'c_clean_roc_pr.png'}")
    except Exception as exc:  # noqa: BLE001
        print(f"figure generation skipped: {type(exc).__name__}")

    print(f"written: {RESULTS / 'c_clean_metrics.csv'}")
    print(f"written: {RESULTS / 'c_clean_model_comparison.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())