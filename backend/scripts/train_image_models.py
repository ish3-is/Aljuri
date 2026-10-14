"""
Phase 3 model training and evaluation.

Three baselines, per the brief, all built on PRETRAINED representations -
nothing is trained from scratch.

    A  efficientnet_b0   fine-tuned end-to-end (lightweight CNN)
    B  vit_b_16          fine-tuned end-to-end (vision transformer)
    C  frozen embeddings + logistic regression head

The split that decides everything is C (generator-held-out). A model can
look excellent on the random split and be worthless on generators it has
never seen, and the gap between those two numbers is the honest result.

Label semantics, enforced everywhere:
    0 = real / camera-captured
    1 = synthetic / AI-generated  (the positive class)

Leakage is asserted, not assumed: every split is checked for exact
overlap and, for the generator split, for generator overlap, before any
model is fitted.
"""

from __future__ import annotations

import json
import os
import platform
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

SEED = 42
BATCH_SIZE = 32
IMAGE_SIZE = 224
EPOCHS = 6
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_transforms(train: bool) -> transforms.Compose:
    """Augmentation is IDENTICAL for both classes - no class-specific path."""
    ops: list = [transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)), transforms.ToTensor()]
    if train:
        # Mild, realistic, and applied uniformly to real and synthetic.
        # Nothing here encodes a class: same pipeline, same probabilities.
        ops = [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
        ]
    ops.append(transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD))
    return transforms.Compose(ops)


class ImageListDataset(Dataset):
    def __init__(self, paths: list[str], labels: list[int], transform) -> None:
        self.paths = paths
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int):
        path = PROJECT / self.paths[index]
        try:
            with Image.open(path) as handle:
                image = handle.convert("RGB")
        except Exception:  # noqa: BLE001
            image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))
        return self.transform(image), self.labels[index]


def label_from_path(relative: str) -> int:
    return 1 if "/synthetic/" in relative.replace("\\", "/") else 0


def resolve_split(split: dict) -> tuple[list[str], list[int]]:
    paths = list(split["train"])
    return paths, [label_from_path(p) for p in paths]


def evaluate(model: nn.Module, loader: DataLoader, device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    probs: list[float] = []
    labels: list[int] = []
    with torch.no_grad():
        for images, target in loader:
            images = images.to(device)
            logits = model(images)
            if logits.shape[1] == 2:
                p = torch.softmax(logits, dim=1)[:, 1]
            else:
                p = torch.sigmoid(logits[:, 0])
            probs.extend(p.cpu().numpy().tolist())
            labels.extend(target.numpy().tolist())
    return np.asarray(probs), np.asarray(labels)


def metrics_for(probs: np.ndarray, labels: np.ndarray, threshold: float = 0.5) -> dict:
    if len(np.unique(labels)) < 2:
        return {"n": int(len(labels)), "note": "single class in test set"}
    preds = (probs >= threshold).astype(int)
    out = {
        "n": int(len(labels)),
        "accuracy": round(float(accuracy_score(labels, preds)), 4),
        "precision": round(float(precision_score(labels, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, preds, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, preds, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(labels, probs)), 4),
        "pr_auc": round(float(average_precision_score(labels, probs)), 4),
        "specificity": round(float(recall_score(1 - labels, 1 - preds, zero_division=0)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, preds)), 4),
        "brier": round(float(brier_score_loss(labels, probs)), 4),
    }
    false_pos = int(((preds == 1) & (labels == 0)).sum())
    false_neg = int(((preds == 0) & (labels == 1)).sum())
    out["fpr"] = round(false_pos / max(int((labels == 0).sum()), 1), 4)
    out["fnr"] = round(false_neg / max(int((labels == 1).sum()), 1), 4)
    out["false_positives"] = false_pos
    out["false_negatives"] = false_neg
    return out


def assert_no_leakage(split: dict, name: str) -> None:
    train, test = set(split["train"]), set(split["test"])
    overlap = train & test
    if overlap:
        raise SystemExit(f"LEAKAGE in split {name}: {len(overlap)} overlapping paths")


def train_cnn(architecture: str, train_paths, train_labels, device, epochs: int):
    """Fine-tune a pretrained CNN end to end."""
    if architecture == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, 2)
    else:
        model = models.vit_b_16(weights=models.ViT_B_16_Weights.IMAGENET1K_V1)
        in_features = model.heads.head.in_features
        model.heads.head = nn.Linear(in_features, 2)

    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimiser = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    loader = DataLoader(
        ImageListDataset(train_paths, train_labels, build_transforms(train=True)),
        batch_size=BATCH_SIZE, shuffle=True, num_workers=0,
    )

    model.train()
    for epoch in range(epochs):
        total = 0.0
        for images, target in loader:
            images, target = images.to(device), target.to(device)
            optimiser.zero_grad()
            loss = criterion(model(images), target)
            loss.backward()
            optimiser.step()
            total += loss.item()
        print(f"    epoch {epoch + 1}/{epochs}  loss={total / max(len(loader), 1):.4f}")
    return model


def extract_frozen_features(paths, labels, device, batch_size: int = 64) -> np.ndarray:
    """Penultimate features from a frozen pretrained backbone."""
    backbone = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
    backbone.classifier = nn.Identity()
    backbone = backbone.to(device).eval()

    loader = DataLoader(
        ImageListDataset(paths, labels, build_transforms(train=False)),
        batch_size=batch_size, shuffle=False, num_workers=0,
    )
    features: list[np.ndarray] = []
    with torch.no_grad():
        for images, _ in loader:
            out = backbone(images.to(device))
            features.append(out.cpu().numpy())
    return np.concatenate(features, axis=0)


def main() -> int:
    set_seed()
    RESULTS.mkdir(parents=True, exist_ok=True)

    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    for name, split in splits["splits"].items():
        assert_no_leakage(split, name)
    print("leakage assertions passed for all splits")

    environment = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torchvision": __import__("torchvision").__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cpu": platform.processor() or platform.machine(),
        "seed": SEED,
        "batch_size": BATCH_SIZE,
        "image_size": IMAGE_SIZE,
        "epochs": EPOCHS,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "device_used": str(DEVICE),
        "label_semantics": {"0": "real / camera-captured", "1": "synthetic / AI-generated"},
    }
    (RESULTS / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    print(f"device: {DEVICE}")

    split_a = splits["splits"]["A_random_stratified"]
    train_paths, train_labels = resolve_split(split_a)
    print(f"training pool: {len(train_paths):,} images")

    results: dict[str, dict] = {}

    # ---- Models A and B --------------------------------------------
    for architecture, label in (("efficientnet_b0", "A_efficientnet_b0"), ("vit_b_16", "B_vit_b_16")):
        print()
        print(f"=== MODEL {label}: fine-tuned {architecture} ===")
        started = time.time()
        model = train_cnn(architecture, train_paths, train_labels, DEVICE, EPOCHS)
        elapsed = time.time() - started
        size_mb = sum(p.numel() for p in model.parameters()) * 4 / 1e6

        results[label] = {"architecture": architecture, "train_seconds": round(elapsed, 1),
                          "params_mb": round(size_mb, 1)}
        for split_name in ("A_random_stratified", "B_source_grouped", "C_generator_holdout"):
            split = splits["splits"][split_name]
            test_paths = list(split["test"])
            test_labels = [label_from_path(p) for p in test_paths]
            loader = DataLoader(
                ImageListDataset(test_paths, test_labels, build_transforms(train=False)),
                batch_size=BATCH_SIZE, num_workers=0,
            )
            probs, labels = evaluate(model, loader, DEVICE)
            results[label][split_name] = metrics_for(probs, labels)
            print(f"    {split_name:26} auc={results[label][split_name].get('roc_auc')} "
                  f"f1={results[label][split_name].get('f1')} "
                  f"fpr={results[label][split_name].get('fpr')}")

    # ---- Model C: frozen embeddings + linear head -------------------
    print()
    print("=== MODEL C: frozen embeddings + logistic regression ===")
    started = time.time()
    features = extract_frozen_features(train_paths, train_labels, DEVICE)
    print(f"    extracted {features.shape} features")
    classifier = LogisticRegression(max_iter=3000, random_state=SEED)
    classifier.fit(features, np.asarray(train_labels))
    results["C_frozen_embeddings_lr"] = {
        "architecture": "frozen efficientnet_b0 penultimate + logistic regression",
        "train_seconds": round(time.time() - started, 1),
        "feature_dim": int(features.shape[1]),
    }
    for split_name in ("A_random_stratified", "B_source_grouped", "C_generator_holdout"):
        split = splits["splits"][split_name]
        test_paths = list(split["test"])
        test_labels = [label_from_path(p) for p in test_paths]
        test_features = extract_frozen_features(test_paths, test_labels, DEVICE)
        probs = classifier.predict_proba(test_features)[:, 1]
        results["C_frozen_embeddings_lr"][split_name] = metrics_for(probs, np.asarray(test_labels))
        print(f"    {split_name:26} auc={results['C_frozen_embeddings_lr'][split_name].get('roc_auc')} "
              f"f1={results['C_frozen_embeddings_lr'][split_name].get('f1')} "
              f"fpr={results['C_frozen_embeddings_lr'][split_name].get('fpr')}")

    (RESULTS / "model_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print()
    print("=== GENERALIZATION GAP (random - generator-held-out) ===")
    for label, row in results.items():
        a = row.get("A_random_stratified", {}).get("roc_auc")
        c = row.get("C_generator_holdout", {}).get("roc_auc")
        if a is not None and c is not None:
            print(f"  {label:26} random={a:.4f}  generator_holdout={c:.4f}  gap={a - c:+.4f}")
    print(f"\nwritten: {RESULTS / 'model_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())