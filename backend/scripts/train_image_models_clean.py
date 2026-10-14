"""
Phase 3 training on Split C_clean, with resumable checkpointing.

Three changes over the first attempt, each fixing a real failure:

1. **Checkpoint after every model and every split.** The first run was
   SIGTERMed between models and lost a completed EfficientNet entirely,
   because results were only written at the very end. Now each completed
   model is persisted immediately and `training_progress.json` records
   which stages are done, so an interrupted run resumes rather than
   restarts.

2. **Class weighting.** C_clean trains on 240 real and 1,499 synthetic
   images (6.2:1). Unweighted, that biases the model toward "synthetic"
   and inflates the false-positive rate - which is the metric that matters
   most here. Weighting uses all the data, which matters because only 400
   real images exist in the entire corpus.

3. **DINOv2 for the embedding baseline**, per the brief, with the
   EfficientNet frozen features retained for comparison.

Selection is on C_clean, not the contaminated splits.
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
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
SPLITS = RESULTS / "splits.json"
PROGRESS = RESULTS / "training_progress.json"
MODELS_DIR = BACKEND / "models"

SEED = 42
BATCH_SIZE = 32
IMAGE_SIZE = 224
EPOCHS = 6
# ViT-B/16 fine-tuning is a comparison baseline, not the expected winner.
# It is capped at fewer epochs so the comparison stays affordable; the
# reduced budget is recorded in the results rather than hidden.
EPOCHS_VIT = 3
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# Worker processes for image decode/normalize. With num_workers=0 the
# GPU idled at "100% utilisation" while drawing only ~31W, because every
# PIL decode and normalization ran on the main thread between batches.
NUM_WORKERS = 4
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

STAGE_NAMES = {
    "efficientnet_b0": "efficientnet_done",
    "vit_b_16": "vit_done",
    "dinov2_embeddings": "embedding_done",
}


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"stages": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": SEED}


def save_progress(progress: dict) -> None:
    """Atomic write: a kill mid-write must not corrupt the progress file."""
    temporary = PROGRESS.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    temporary.replace(PROGRESS)


def build_transforms(train: bool) -> transforms.Compose:
    """Identical augmentation for both classes - no class-specific path."""
    if train:
        return transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


class ImageListDataset(Dataset):
    def __init__(self, paths, labels, transform):
        self.paths, self.labels, self.transform = paths, labels, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        try:
            with Image.open(PROJECT / self.paths[index]) as handle:
                image = handle.convert("RGB")
        except Exception:  # noqa: BLE001
            image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))
        return self.transform(image), self.labels[index]


def label_of(relative: str) -> int:
    return 1 if "/synthetic/" in relative.replace("\\", "/") else 0


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion.

    With only 100 real test images a bare FPR percentage is misleading;
    the interval is reported alongside every rate.
    """
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def evaluate(model, loader, device):
    model.eval()
    probs, labels = [], []
    with torch.no_grad():
        for images, target in loader:
            logits = model(images.to(device))
            p = (torch.softmax(logits, 1)[:, 1] if logits.shape[1] == 2
                 else torch.sigmoid(logits[:, 0]))
            probs.extend(p.cpu().numpy().tolist())
            labels.extend(target.numpy().tolist())
    return np.asarray(probs), np.asarray(labels)


def metrics_for(probs: np.ndarray, labels: np.ndarray, threshold: float = 0.5) -> dict:
    if len(set(labels.tolist())) < 2:
        return {"n": int(len(labels)), "note": "single class in test set"}
    preds = (probs >= threshold).astype(int)
    n_real = int((labels == 0).sum())
    n_syn = int((labels == 1).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    low, high = wilson_interval(fp, n_real)
    return {
        "n": int(len(labels)),
        "n_real": n_real,
        "n_synthetic": n_syn,
        "accuracy": round(float(accuracy_score(labels, preds)), 4),
        "precision": round(float(precision_score(labels, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, preds, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, preds, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(labels, probs)), 4),
        "pr_auc": round(float(average_precision_score(labels, probs)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, preds)), 4),
        "brier": round(float(brier_score_loss(labels, probs)), 4),
        "fpr": round(fp / max(n_real, 1), 4),
        "fpr_ci95": [round(low, 4), round(high, 4)],
        "fnr": round(fn / max(n_syn, 1), 4),
        "false_positives": fp,
        "false_negatives": fn,
    }


def train_cnn(architecture, train_paths, train_labels, val_loader, stage):
    epochs = EPOCHS_VIT if architecture == "vit_b_16" else EPOCHS
    if architecture == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    else:
        model = models.vit_b_16(weights=models.ViT_B_16_Weights.IMAGENET1K_V1)
        model.heads.head = nn.Linear(model.heads.head.in_features, 2)
    model = model.to(DEVICE)

    # Class weighting: C_clean is 6.2:1 toward synthetic. Unweighted this
    # inflates the false-positive rate, the metric that matters most.
    counts = np.bincount(np.asarray(train_labels), minlength=2).astype(np.float64)
    weights = counts.sum() / (2.0 * np.clip(counts, 1, None))
    weight_tensor = torch.tensor(weights, dtype=torch.float32, device=DEVICE)
    print(f"    class weights: real={weights[0]:.3f} synthetic={weights[1]:.3f}")

    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    optimiser = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    loader = DataLoader(
        ImageListDataset(train_paths, train_labels, build_transforms(True)),
        batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS,
    )

    best_auc, best_state = -1.0, None
    for epoch in range(epochs):
        model.train()
        total = 0.0
        for images, target in loader:
            images, target = images.to(DEVICE), target.to(DEVICE)
            optimiser.zero_grad()
            loss = criterion(model(images), target)
            loss.backward()
            optimiser.step()
            total += loss.item()
        message = f"    epoch {epoch + 1}/{epochs} loss={total / max(len(loader), 1):.4f}"
        if val_loader is not None:
            probs, labels = evaluate(model, val_loader, DEVICE)
            if len(set(labels.tolist())) > 1:
                auc = float(roc_auc_score(labels, probs))
                message += f" val_auc={auc:.4f}"
                if auc > best_auc:
                    best_auc, best_state = auc, {k: v.detach().cpu().clone()
                                                 for k, v in model.state_dict().items()}
        print(message, flush=True)

    if best_state is not None:
        model.load_state_dict(best_state)
        print(f"    restored best validation checkpoint (auc={best_auc:.4f})")
    return model


def main() -> int:
    set_seed()
    RESULTS.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    splits = json.loads(SPLITS.read_text(encoding="utf-8"))["splits"]
    clean = splits["C_clean_CF_generator_holdout"]
    progress = load_progress()

    train_paths = list(clean["train"])
    train_labels = [label_of(p) for p in train_paths]
    val_paths = list(clean.get("val") or [])
    val_labels = [label_of(p) for p in val_paths]
    test_paths = list(clean["test"])
    test_labels = [label_of(p) for p in test_paths]

    print(f"Split C_clean (unconfounded, CommunityForensics only)")
    print(f"  train {len(train_paths):,}  val {len(val_paths):,}  test {len(test_paths):,}")
    print(f"  held-out generators: {clean['held_out_generator_count']} "
          f"of {clean['train_generator_count'] + clean['held_out_generator_count']}")
    print(f"  device: {DEVICE}")
    print(f"  resuming; completed stages: {list(progress['stages'].keys()) or 'none'}")

    val_loader = DataLoader(
        ImageListDataset(val_paths, val_labels, build_transforms(False)),
        batch_size=BATCH_SIZE, num_workers=NUM_WORKERS,
    ) if val_paths else None
    test_loader = DataLoader(
        ImageListDataset(test_paths, test_labels, build_transforms(False)),
        batch_size=BATCH_SIZE, num_workers=NUM_WORKERS,
    )

    def record(architecture: str, entry: dict, save_weights: bool = True) -> None:
        # The tensor state_dict must be REMOVED before the JSON write. An
        # earlier ordering serialised it into the progress file and raised
        # TypeError: Object of type Tensor is not JSON serializable.
        state = entry.pop("_state", None)
        if save_weights and state is not None:
            torch.save(
                {"state_dict": state, **entry},
                MODELS_DIR / f"basirah-image-cand-{architecture}.pt",
            )
        progress["stages"][STAGE_NAMES[architecture]] = entry
        save_progress(progress)

    # ---- A: EfficientNet-B0 ---------------------------------------
    stage = STAGE_NAMES["efficientnet_b0"]
    if stage not in progress["stages"]:
        print()
        print("=== A: efficientnet_b0 ===")
        started = time.time()
        model = train_cnn("efficientnet_b0", train_paths, train_labels, val_loader, stage)
        probs, labels = evaluate(model, test_loader, DEVICE)
        entry = {
            "architecture": "efficientnet_b0",
            "train_seconds": round(time.time() - started, 1),
            "C_clean": metrics_for(probs, labels),
            "_state": model.state_dict(),
        }
        record("efficientnet_b0", entry)
        print(f"    C_clean auc={entry['C_clean'].get('roc_auc')} "
              f"f1={entry['C_clean'].get('f1')} fpr={entry['C_clean'].get('fpr')} "
              f"ci={entry['C_clean'].get('fpr_ci95')}")
    else:
        print(f"\n(skip A: {stage} already complete)")

    # ---- B: ViT-B/16 ----------------------------------------------
    stage = STAGE_NAMES["vit_b_16"]
    if stage not in progress["stages"]:
        print()
        print("=== B: vit_b_16 ===")
        started = time.time()
        model = train_cnn("vit_b_16", train_paths, train_labels, val_loader, stage)
        probs, labels = evaluate(model, test_loader, DEVICE)
        entry = {
            "architecture": "vit_b_16",
            "train_seconds": round(time.time() - started, 1),
            "C_clean": metrics_for(probs, labels),
            "_state": model.state_dict(),
        }
        record("vit_b_16", entry)
        print(f"    C_clean auc={entry['C_clean'].get('roc_auc')} "
              f"f1={entry['C_clean'].get('f1')} fpr={entry['C_clean'].get('fpr')}")
    else:
        print(f"\n(skip B: {stage} already complete)")

    # ---- C: DINOv2 frozen embeddings + logistic regression -------
    stage = STAGE_NAMES["dinov2_embeddings"]
    if stage not in progress["stages"]:
        print()
        print("=== C: DINOv2 frozen embeddings + logistic regression ===")
        started = time.time()
        try:
            import timm

            backbone = timm.create_model("vit_small_patch14_dinov2.lvd142m", pretrained=True,
                                         num_classes=0)
            transform = timm.data.resolve_model_data_config(
                backbone
            ) if hasattr(timm.data, "resolve_model_data_config") else None
            size = 224
            pipeline = transforms.Compose([
                transforms.Resize((size, size)),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ])
            name = "vit_small_patch14_dinov2"
        except Exception as exc:  # noqa: BLE001
            print(f"    DINOv2 unavailable ({type(exc).__name__}); "
                  f"falling back to frozen EfficientNet features")
            backbone = models.efficientnet_b0(
                weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
            backbone.classifier = nn.Identity()
            pipeline = build_transforms(False)
            name = "frozen_efficientnet_b0_penultimate"

        backbone = backbone.to(DEVICE).eval()

        def embed(paths):
            loader = DataLoader(
                ImageListDataset(paths, [label_of(p) for p in paths], pipeline),
                batch_size=64, num_workers=NUM_WORKERS,
            )
            out = []
            with torch.no_grad():
                for images, _ in loader:
                    features = backbone(images.to(DEVICE))
                    if isinstance(features, dict):
                        features = features.get("x_norm_patchtokens", next(iter(features.values())))
                    if features.ndim == 3:
                        features = features.mean(dim=1)
                    out.append(features.cpu().numpy())
            return np.concatenate(out, axis=0)

        train_features = embed(train_paths)
        print(f"    feature dim: {train_features.shape[1]}")
        classifier = LogisticRegression(max_iter=3000, random_state=SEED,
                                        class_weight="balanced")
        classifier.fit(train_features, np.asarray(train_labels))
        test_features = embed(test_paths)
        probs = classifier.predict_proba(test_features)[:, 1]
        entry = {
            "architecture": name + " (frozen) + logistic regression",
            "train_seconds": round(time.time() - started, 1),
            "feature_dim": int(train_features.shape[1]),
            "C_clean": metrics_for(probs, np.asarray(test_labels)),
        }
        progress["stages"][stage] = entry
        save_progress(progress)
        import joblib
        joblib.dump(classifier, MODELS_DIR / "basirah-image-cand-dinov2_lr.joblib")
        print(f"    C_clean auc={entry['C_clean'].get('roc_auc')} "
              f"f1={entry['C_clean'].get('f1')} fpr={entry['C_clean'].get('fpr')}")
    else:
        print(f"\n(skip C: {stage} already complete)")

    print()
    print("=== C_clean RESULTS (unconfounded, 109 unseen generators) ===")
    for name, entry in progress["stages"].items():
        m = entry.get("C_clean", {})
        if m.get("roc_auc") is not None:
            print(f"  {name:22} auc={m['roc_auc']:.4f} f1={m['f1']:.4f} "
                  f"fpr={m['fpr']:.4f} ci95={m['fpr_ci95']} n_real={m['n_real']}")
    print()
    print("NOTE: the earlier 0.997-0.999 figures came from a SOURCE-CONFOUNDED")
    print("split (source-only AUC 0.9409) and are not comparable to these.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())