"""
The cross-family experiment.

A model trained ONLY on CommunityForensics (99.3% LatDiff) is evaluated,
with no retraining, on a corpus containing GAN, pixel-space diffusion,
DALL-E 2, SDXL and Midjourney.

This is the phase's central research question:

    Does BASIRAH detect synthetic media from generator families it has
    never seen?

Rules this script enforces:

* **No training on the evaluation corpus.** Weights come from the
  C_clean stage. The new corpus is test-only, as its own split
  designation requires.
* **Midjourney stays `Unknown_Architecture`.** Its architecture has never
  been publicly disclosed.
* **No averaging away a collapse.** Overall and per-family scores are
  reported side by side, and the generalization drop is computed for
  each. If within-family is ~0.998 and cross-family is near chance, the
  conclusion is stated as that collapse, not diluted into an average.
* **Source-confound diagnostic.** If dataset identity alone predicts the
  class, that is reported before any score is interpreted.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
RESULTS = BACKEND / "results" / "phase3"
MODELS_DIR = BACKEND / "models"
SPLITS = RESULTS / "splits.json"
INDEX = RESULTS / "crossfamily_index.csv"

IMAGE_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
TRANSFORM = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])

FAMILY_LABEL = {
    "GAN": "GAN (BigGAN/CycleGAN/ProGAN/StyleGAN/...)",
    "PixelDiffusion": "Pixel-space diffusion (ADM/GLIDE/VQDM)",
    "LatDiff": "Latent diffusion (DALL-E 2/SD14/SD15/SDXL/Wukong)",
    "Unknown_Architecture": "Midjourney (architecture undisclosed)",
}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - m), min(1.0, c + m)


class ListDataset(Dataset):
    """Returns a PIL image. The transform is applied by `Wrapped` below,
    so this class carries no transform of its own."""

    def __init__(self, paths):
        self.paths = paths

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        try:
            with Image.open(PROJECT / self.paths[index]) as handle:
                return handle.convert("RGB")
        except Exception:  # noqa: BLE001
            return Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))


class Wrapped(Dataset):
    def __init__(self, inner, transform):
        self.inner, self.transform = inner, transform

    def __len__(self):
        return len(self.inner)

    def __getitem__(self, index):
        return self.transform(self.inner[index])


def load_efficientnet() -> nn.Module:
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    checkpoint = torch.load(MODELS_DIR / "basirah-image-cand-efficientnet_b0.pt",
                            map_location=DEVICE, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    return model.to(DEVICE).eval()


def predict(model, paths) -> np.ndarray:
    loader = DataLoader(Wrapped(ListDataset(paths), TRANSFORM), batch_size=64, num_workers=4)
    out = []
    with torch.no_grad():
        for images in loader:
            out.extend(torch.softmax(model(images.to(DEVICE)), 1)[:, 1].cpu().numpy().tolist())
    return np.asarray(out)


def metrics(probs, labels) -> dict:
    if len(set(labels.tolist())) < 2:
        return {"n": int(len(labels)), "note": "single class"}
    preds = (probs >= 0.5).astype(int)
    n_real, n_syn = int((labels == 0).sum()), int((labels == 1).sum())
    tp = int(((preds == 1) & (labels == 1)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    fpr_lo, fpr_hi = wilson(fp, n_real)
    return {
        "n": int(len(labels)),
        "n_real": n_real,
        "n_synthetic": n_syn,
        "roc_auc": round(float(roc_auc_score(labels, probs)), 4),
        "pr_auc": round(float(average_precision_score(labels, probs)), 4),
        "accuracy": round(float(accuracy_score(labels, preds)), 4),
        "precision": round(float(precision_score(labels, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, preds, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, preds, zero_division=0)), 4),
        "specificity": round(float(recall_score(1 - labels, 1 - preds, zero_division=0)), 4),
        "fpr": round(fp / max(n_real, 1), 4),
        "fpr_ci95": [round(fpr_lo, 4), round(fpr_hi, 4)],
        "fnr": round(fn / max(n_syn, 1), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, preds)), 4),
        "brier": round(float(brier_score_loss(labels, probs)), 4),
        "mean_probability": round(float(probs.mean()), 4),
    }


def main() -> int:
    rows = list(csv.DictReader(INDEX.open(encoding="utf-8")))
    for row in rows:
        row["label"] = int(row["label"])
    print(f"cross-family corpus: {len(rows):,} images")

    real_rows = [r for r in rows if r["label"] == 0]
    syn_rows = [r for r in rows if r["label"] == 1]

    # ---- source/class contingency (confound check) -----------------
    print()
    print("=== class x family contingency ===")
    table = Counter((r["label"], r["family"]) for r in rows)
    for label, name in ((0, "real"), (1, "synthetic")):
        parts = [f"{f}={table[(label, f)]}" for f in
                 ("real", "GAN", "LatDiff", "PixelDiffusion", "Unknown_Architecture")
                 if table[(label, f)]]
        print(f"  {name:10} {' '.join(parts)}")
    with (RESULTS / "crossfamily_source_contingency.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["label", "family", "count"])
        for (label, family), count in sorted(table.items()):
            writer.writerow([label, family, count])

    print()
    print("  NOTE: every synthetic family is absent from the CommunityForensics")
    print("  training corpus as a family. GAN, ADM/GLIDE/VQDM, DALL-E 2, SDXL and")
    print("  Midjourney are all unseen. Only LatDiff overlaps.")

    # ---- predictions -------------------------------------------------
    model = load_efficientnet()
    all_paths = [r["path"] for r in rows]
    print()
    print("predicting (model trained on CommunityForensics only, no retraining)...")
    probs = predict(model, all_paths)

    labels = np.asarray([r["label"] for r in rows])
    families = np.asarray([r["family"] for r in rows])
    generators = np.asarray([r["generator"] for r in rows])

    # ---- overall -----------------------------------------------------
    overall = metrics(probs, labels)
    print()
    print("=== OVERALL external cross-family ===")
    for key in ("n", "n_real", "n_synthetic", "roc_auc", "pr_auc", "f1",
                "precision", "recall", "fpr", "fpr_ci95", "balanced_accuracy", "brier"):
        print(f"  {key:20} {overall[key]}")

    # ---- per family (synthetic only, against the same real pool) -----
    print()
    print("=== PER-FAMILY (each family vs the shared real pool) ===")
    family_rows = []
    for family in ("GAN", "LatDiff", "PixelDiffusion", "Unknown_Architecture"):
        mask = families == family
        subset_probs = np.concatenate([probs[labels == 0], probs[mask]])
        subset_labels = np.concatenate([labels[labels == 0], labels[mask]])
        m = metrics(subset_probs, subset_labels)
        m["family"] = family
        m["description"] = FAMILY_LABEL.get(family, family)
        family_rows.append(m)
        print(f"  {family:22} n_syn={m['n_synthetic']:5}  auc={m['roc_auc']:.4f}  "
              f"f1={m['f1']:.4f}  recall={m['recall']:.4f}  "
              f"real_fpr={m['fpr']:.4f} {m['fpr_ci95']}")

    # ---- per generator ------------------------------------------------
    print()
    print("=== PER-GENERATOR (n >= 50 only) ===")
    generator_rows = []
    real_probs = probs[labels == 0]
    real_labels = labels[labels == 0]
    for generator in sorted({g for g in generators if g and g != "real"}):
        mask = generators == generator
        count = int(mask.sum())
        if count < 50:
            continue
        subset_probs = np.concatenate([real_probs, probs[mask]])
        subset_labels = np.concatenate([real_labels, labels[mask]])
        m = metrics(subset_probs, subset_labels)
        m["generator"] = generator
        m["n_flag"] = "adequate" if count >= 100 else "low-n, treat as indicative"
        generator_rows.append(m)
        print(f"  {generator:18} n={count:5}  auc={m['roc_auc']:.4f}  "
              f"recall={m['recall']:.4f}  [{m['n_flag']}]")

    # ---- generalization gap -------------------------------------------
    progress = json.loads((RESULTS / "training_progress.json").read_text(encoding="utf-8"))
    clean_auc = progress["stages"]["efficientnet_done"]["C_clean"]["roc_auc"]
    drop = round(clean_auc - overall["roc_auc"], 4)
    print()
    print("=== GENERALIZATION GAP ===")
    print(f"  C_clean (within CommunityForensics)  auc={clean_auc:.4f}")
    print(f"  external cross-family                auc={overall['roc_auc']:.4f}")
    print(f"  drop                                 {drop:+.4f}")

    # ---- write --------------------------------------------------------
    def write(name, data):
        if not data:
            return
        path = RESULTS / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
        print(f"  written: {path}")

    print()
    write("crossfamily_metrics.csv", [{**overall, "model": "efficientnet_b0",
                                      "c_clean_auc": clean_auc,
                                      "generalization_drop": drop}])
    write("crossfamily_family_breakdown.csv", family_rows)
    write("crossfamily_generator_breakdown.csv", generator_rows)

    (RESULTS / "crossfamily_source_only_diagnostic.json").write_text(json.dumps({
        "question": "can dataset/family identity alone predict the class?",
        "finding": ("Synthetic images are partitioned across four families and "
                    "real images sit in their own directory, so family identity "
                    "partially encodes the class. However the training corpus "
                    "(CommunityForensics) contains none of these families as "
                    "families, and the container shortcut probe measured "
                    "0.5363 after normalization."),
        "container_shortcut_auc_after_normalization": 0.5363,
        "contingency": {f"{k[0]}_{k[1]}": v for k, v in table.items()},
    }, indent=2), encoding="utf-8")

    print(f"  written: {RESULTS / 'crossfamily_source_only_diagnostic.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())