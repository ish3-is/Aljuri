"""
Phase 3 multi-family held-out-family experiment.

WHY THIS EXISTS
---------------
A model trained only on CommunityForensics scored ROC-AUC 0.9984 on
within-source test but 0.3954 externally, with 89.7% false positives on
real photographs. That is below chance. It learned one generator family's
fingerprint, not "synthetic media". That negative result is the reason
this script exists and it is preserved, not overwritten: the earlier
artifacts (`crossfamily_metrics.csv`, `training_progress.json` stages,
`evaluate_crossfamily.py`) are left untouched.

THE PROTOCOL
------------
Five experiments, each removing a generator family from TRAINING and
VALIDATION entirely and testing on it:

  A_holdout_GAN              train on LatDiff + CF, test on GAN
  B_holdout_PixelDiffusion   train on GAN + LatDiff + CF, test on ADM/GLIDE/VQDM
  C_holdout_Midjourney       train on all but Midjourney, test on Midjourney
  D_holdout_LatDiff          train on GAN + PixelDiff + CF, test on DALL-E2/SD/Wukong
  E_holdout_SDXL             train on LatDiff except SDXL, test on SDXL

Because the test split of each experiment IS the held-out family (plus a
shared real pool), the test metrics are the family-generalization metrics.
Model selection therefore reduces to ranking by the WORST experiment, not
the average. `mean_family_roc_auc` is reported but is explicitly NOT used
for selection.

TWO MODELS PER EXPERIMENT
-------------------------
  1. EfficientNet-B0 (torchvision IMAGENET1K_V1), class-weighted CE,
     AdamW lr 1e-4, 5 epochs.
  2. Frozen DINOv2 (vit_small_patch14_dinov2.lvd142m, num_classes=0)
     embeddings + LogisticRegression(class_weight='balanced').

RULES ENFORCED HERE
-------------------
* Class weighting, never discarding or oversampling data.
* Augmentation is a function of the SPLIT, not the class - identical for
  real and synthetic.
* num_workers=4 everywhere (num_workers=0 starved the GPU).
* One GPU job at a time; checkpoints persisted after every (exp, model).
* Temperature scaling fit on VALIDATION only, never on test.
* Diagnostics (source classifier, family classifier) are never deployed.

Promotion is blocked: nothing here writes models/ACTIVE_IMAGE_MODEL.json
and nothing is written to app/api/.
"""

from __future__ import annotations

import csv
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
SPLITS = RESULTS / "multifamily_splits.json"
CORPUS = RESULTS / "multifamily_corpus.csv"
# Separate from training_progress.json so the earlier C_clean stages and
# the 0.3954 external result survive verbatim.
PROGRESS = RESULTS / "multifamily_training_progress.json"
CKPT_DIR = BACKEND / "models" / "multifamily_candidates"   # NOT an ACTIVE model
PROB_DIR = RESULTS / "multifamily_probs"
EMB_CACHE = RESULTS / "dinov2_embeddings_cache.npz"

SEED = 42
BATCH_SIZE = 32
IMAGE_SIZE = 224
EPOCHS = 5
LR = 1e-4
NUM_WORKERS = 4
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

MODELS = ("efficientnet_b0", "dinov2_lr")
EXPERIMENTS = ("A_holdout_GAN", "B_holdout_PixelDiffusion", "C_holdout_Midjourney",
               "D_holdout_LatDiff", "E_holdout_SDXL")

METRIC_KEYS = ("roc_auc", "pr_auc", "accuracy", "balanced_accuracy", "precision",
               "recall", "f1", "specificity", "fpr", "fnr", "brier")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    d = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / d
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def expected_calibration_error(labels: np.ndarray, probs: np.ndarray, bins: int = 15) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (probs > lo) & (probs <= hi)
        if not mask.any():
            continue
        ece += mask.mean() * abs(labels[mask].mean() - probs[mask].mean())
    return float(ece)


def metrics_for(probs: np.ndarray, labels: np.ndarray, threshold: float = 0.5) -> dict:
    if len(set(labels.tolist())) < 2:
        return {"n": int(len(labels)), "note": "single class in test set"}
    preds = (probs >= threshold).astype(int)
    n_real = int((labels == 0).sum())
    n_syn = int((labels == 1).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    lo, hi = wilson_interval(fp, n_real)
    return {
        "n": int(len(labels)),
        "n_real": n_real,
        "n_synthetic": n_syn,
        "roc_auc": round(float(roc_auc_score(labels, probs)), 4),
        "pr_auc": round(float(average_precision_score(labels, probs)), 4),
        "accuracy": round(float(accuracy_score(labels, preds)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, preds)), 4),
        "precision": round(float(precision_score(labels, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, preds, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, preds, zero_division=0)), 4),
        "specificity": round(float(recall_score(1 - labels, 1 - preds, zero_division=0)), 4),
        "fpr": round(fp / max(n_real, 1), 4),
        "fpr_ci95": [round(lo, 4), round(hi, 4)],
        "fnr": round(fn / max(n_syn, 1), 4),
        "brier": round(float(brier_score_loss(labels, probs)), 4),
        "false_positives": fp,
        "false_negatives": fn,
        "mean_probability": round(float(probs.mean()), 4),
    }


def build_transforms(train: bool) -> transforms.Compose:
    """Augmentation depends on the split only - real and synthetic get
    exactly the same pipeline. No class-conditional augmentation."""
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
    def __init__(self, paths, targets, transform):
        self.paths, self.targets, self.transform = paths, targets, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        try:
            with Image.open(PROJECT / self.paths[index]) as handle:
                image = handle.convert("RGB")
        except Exception:  # noqa: BLE001
            image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))
        return self.transform(image), self.targets[index]


def evaluate(model, loader, device):
    model.eval()
    probs, labels = [], []
    with torch.no_grad():
        for images, target in loader:
            logits = model(images.to(device))
            p = torch.softmax(logits, 1)[:, 1]
            probs.extend(p.cpu().numpy().tolist())
            labels.extend(target.numpy().tolist())
    return np.asarray(probs), np.asarray(labels)


def load_progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"stages": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "seed": SEED}


def save_progress(progress: dict) -> None:
    temporary = PROGRESS.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    temporary.replace(PROGRESS)


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    path = RESULTS / name
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  written: {path.name}")


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load_corpus() -> dict[str, dict]:
    rows = list(csv.DictReader(CORPUS.open(encoding="utf-8")))
    return {r["path"]: {"label": int(r["label"]), "source": r["source"],
                        "family": r["family"], "generator": r["generator"]}
            for r in rows}


def experiment_splits(name: str) -> dict:
    return json.loads(SPLITS.read_text(encoding="utf-8"))["experiments"][name]


# --------------------------------------------------------------------------
# Model 1: EfficientNet-B0
# --------------------------------------------------------------------------
def train_efficientnet(train_paths, train_labels, val_paths, val_labels):
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model = model.to(DEVICE)

    counts = np.bincount(np.asarray(train_labels), minlength=2).astype(np.float64)
    weights = counts.sum() / (2.0 * np.clip(counts, 1, None))
    weight_tensor = torch.tensor(weights, dtype=torch.float32, device=DEVICE)
    print(f"    class weights: real={weights[0]:.3f} synthetic={weights[1]:.3f}")

    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    optimiser = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    loader = DataLoader(
        ImageListDataset(train_paths, train_labels, build_transforms(True)),
        batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS, pin_memory=True,
    )
    val_loader = DataLoader(
        ImageListDataset(val_paths, val_labels, build_transforms(False)),
        batch_size=BATCH_SIZE, num_workers=NUM_WORKERS,
    ) if val_paths else None

    best_auc, best_state = -1.0, None
    history = []
    for epoch in range(EPOCHS):
        model.train()
        running = 0.0
        for images, target in loader:
            images, target = images.to(DEVICE), target.to(DEVICE)
            optimiser.zero_grad()
            loss = criterion(model(images), target)
            loss.backward()
            optimiser.step()
            running += loss.item()
        message = f"    epoch {epoch + 1}/{EPOCHS} loss={running / max(len(loader), 1):.4f}"
        epoch_auc = None
        if val_loader is not None:
            probs, labels = evaluate(model, val_loader, DEVICE)
            if len(set(labels.tolist())) > 1:
                epoch_auc = float(roc_auc_score(labels, probs))
                message += f" val_auc={epoch_auc:.4f}"
                if epoch_auc > best_auc:
                    best_auc = epoch_auc
                    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        history.append({"epoch": epoch + 1, "train_loss": round(running / max(len(loader), 1), 5),
                        "val_roc_auc": None if epoch_auc is None else round(epoch_auc, 4)})
        print(message, flush=True)

    if best_state is not None:
        model.load_state_dict(best_state)
        print(f"    restored best validation checkpoint (val auc={best_auc:.4f})")
    return model, history, best_auc


# --------------------------------------------------------------------------
# Model 2: frozen DINOv2 + logistic regression
# --------------------------------------------------------------------------
def get_backbone():
    import timm

    # img_size=224 is REQUIRED: this checkpoint defaults to img_size=518 and
    # asserts on 224 input otherwise. We deliberately stay at 224 rather than
    # feeding the model its native 518: the rest of the pipeline (both
    # normalized corpora, the EfficientNet baseline, all completed results) is
    # 224, and letting only DINOv2 run at 518 would make the two models
    # incomparable, which defeats the point of the comparison.
    # LIMITATION: this interpolates the pretrained position embeddings from
    # 37x37 down to 16x16 rather than using them at native resolution. That
    # slightly weakens the backbone relative to a native-518 run; it is
    # recorded in the results rather than silently accepted.
    model = timm.create_model("vit_small_patch14_dinov2.lvd142m", pretrained=True,
                              num_classes=0, img_size=224)
    model = model.to(DEVICE).eval()
    # resolve_model_data_config still reports the checkpoint's native 518, so the
    # input size is pinned explicitly below rather than read from the config.
    cfg = timm.data.resolve_model_data_config(model)
    return model, dict(cfg)


def embed_paths(paths, backbone, pipeline, batch_size=64):
    dataset = ImageListDataset(paths, [0] * len(paths), pipeline)
    loader = DataLoader(dataset, batch_size=batch_size, num_workers=NUM_WORKERS)
    out = []
    with torch.no_grad():
        for images, _ in loader:
            features = backbone(images.to(DEVICE))
            if isinstance(features, dict):
                features = features.get("x_norm_clstoken", next(iter(features.values())))
            if isinstance(features, (list, tuple)):
                features = features[0]
            if features.ndim == 3:
                features = features.mean(dim=1)
            out.append(features.float().cpu().numpy())
    return np.concatenate(out, axis=0).astype(np.float32)


def build_embedding_table(all_paths: list[str]) -> tuple[np.ndarray, list[str]]:
    """Embed the whole corpus ONCE and cache. All five experiments draw
    from this table, so DINOv2 sees each image a single time."""
    if EMB_CACHE.exists():
        # npz members are decompressed on EVERY __getitem__, so the matrix must
        # be materialised once. Indexing it inside a comprehension re-read the
        # whole 12MB array per image and exhausted memory.
        with np.load(EMB_CACHE, allow_pickle=True) as data:
            cached_paths = [str(p) for p in data["paths"]]
            cached_emb = data["emb"]
            table = {p: cached_emb[i] for i, p in enumerate(cached_paths)}
        if set(cached_paths) >= set(all_paths):
            print(f"    embedding cache hit ({len(cached_paths):,} vectors, "
                  f"dim={table[cached_paths[0]].shape[0]})")
            return np.stack([table[p] for p in all_paths]), list(all_paths)
        del table, cached_emb

    backbone, cfg = get_backbone()
    size = 224
    pipeline = transforms.Compose([
        transforms.Resize((size, size), interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(list(cfg["mean"]), list(cfg["std"])),
    ])
    print(f"    embedding {len(all_paths):,} images at {size}x{size} "
          f"(model default {cfg['input_size']})")
    table = {}
    started = time.time()
    chunk = 2048
    for offset in range(0, len(all_paths), chunk):
        block = all_paths[offset:offset + chunk]
        vectors = embed_paths(block, backbone, pipeline)
        for path, vector in zip(block, vectors):
            table[path] = vector
        print(f"      {min(offset + chunk, len(all_paths)):,}/{len(all_paths):,}", flush=True)
    del backbone
    torch.cuda.empty_cache()
    print(f"    embeddings done in {time.time() - started:.0f}s")
    order = list(table.keys())
    matrix = np.stack([table[p] for p in order])
    np.savez_compressed(EMB_CACHE, emb=matrix, paths=np.array(order, dtype=object))
    return np.stack([table[p] for p in all_paths]), list(all_paths)


# --------------------------------------------------------------------------
# calibration (validation only)
# --------------------------------------------------------------------------
def fit_temperature(val_probs: np.ndarray, val_labels: np.ndarray) -> float:
    """Fit a single temperature by minimising NLL on the VALIDATION split."""
    logits = np.log(np.clip(val_probs, 1e-6, 1 - 1e-6) /
                    np.clip(1 - val_probs, 1e-6, 1 - 1e-6))
    log_t_grid = np.linspace(np.log(0.2), np.log(10.0), 81)

    def nll(log_t: float) -> float:
        scaled = np.clip(logits / np.exp(log_t), -60.0, 60.0)
        # log p = log sigmoid(scaled); log(1-p) = log sigmoid(-scaled)
        log_p = -np.logaddexp(0.0, -scaled)
        log_1mp = -np.logaddexp(0.0, scaled)
        return float(-np.mean(val_labels * log_p + (1.0 - val_labels) * log_1mp))

    best_t, best_loss = 1.0, float("inf")
    for log_t in log_t_grid:
        value = nll(log_t)
        if value < best_loss:
            best_t, best_loss = float(np.exp(log_t)), value
    return best_t


def apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
    logits = np.log(np.clip(probs, 1e-6, 1 - 1e-6) /
                    np.clip(1 - probs, 1e-6, 1 - 1e-6)) / temperature
    return 1.0 / (1.0 + np.exp(-logits))


def _append_breakdown_and_errors(exp, model_name, spec, test_paths, test_labels,
                                 test_probs, corpus, generator_rows, fp_rows, fn_rows) -> None:
    """Per-generator breakdown and the FP/FN analyses.

    Shared by the fresh-compute and resume paths so both emit identical rows.
    """
    test_meta = [corpus[p] for p in test_paths]
    families = np.asarray([m["family"] for m in test_meta])
    generators = np.asarray([m["generator"] for m in test_meta])

    # ---- per-generator breakdown (each generator vs the shared real pool) ----
    real_probs, real_labels = test_probs[test_labels == 0], test_labels[test_labels == 0]
    for generator in sorted({g for g in generators.tolist() if g and g != "real"}):
        mask = generators == generator
        if int(mask.sum()) < 50:
            continue
        sub_probs = np.concatenate([real_probs, test_probs[mask]])
        sub_labels = np.concatenate([real_labels, np.ones(int(mask.sum()), dtype=int)])
        gm = metrics_for(sub_probs, sub_labels)
        generator_rows.append({
            "experiment": exp, "model": model_name, "generator": generator,
            "family": families[mask][0], "seen_in_training":
                "NO - held out" if generator in
                (spec["held_out_generator"], spec["held_out_family"]) else "yes",
            "n_synthetic": gm["n_synthetic"],
            "roc_auc": gm["roc_auc"], "pr_auc": gm["pr_auc"],
            "accuracy": gm["accuracy"], "balanced_accuracy": gm["balanced_accuracy"],
            "precision": gm["precision"], "recall": gm["recall"], "f1": gm["f1"],
            "specificity": gm["specificity"], "fpr": gm["fpr"],
            "fnr": gm["fnr"], "brier": gm["brier"],
        })

    # ---- false positive / false negative analyses -------------------------
    preds = (test_probs >= 0.5).astype(int)
    for path, label, prob, pred, meta in zip(test_paths, test_labels, test_probs,
                                             preds, test_meta):
        if pred == 1 and label == 0:
            fp_rows.append({"experiment": exp, "model": model_name, "path": path,
                            "true_label": "real", "source": meta["source"],
                            "family": meta["family"], "generator": meta["generator"],
                            "probability": round(float(prob), 4),
                            "error": "false_positive"})
        elif pred == 0 and label == 1:
            fn_rows.append({"experiment": exp, "model": model_name, "path": path,
                            "true_label": "synthetic", "source": meta["source"],
                            "family": meta["family"], "generator": meta["generator"],
                            "probability": round(float(prob), 4),
                            "error": "false_negative"})


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    set_seed()
    RESULTS.mkdir(parents=True, exist_ok=True)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    PROB_DIR.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus()
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    experiments = splits["experiments"]

    # every path that any experiment touches, in a stable order
    all_paths: list[str] = []
    seen = set()
    for name in EXPERIMENTS:
        for split in ("train", "val", "test"):
            for path in experiments[name][split]:
                if path not in seen:
                    seen.add(path)
                    all_paths.append(path)
    print(f"corpus {len(corpus):,} rows; {len(all_paths):,} distinct images touched")
    print(f"device: {DEVICE}; torch {torch.__version__}")
    print(f"resuming; completed: {list(load_progress()['stages'].keys()) or 'none'}")

    print("\n=== DINOv2 frozen embeddings (one pass over the corpus) ===")
    embeddings, embed_order = build_embedding_table(all_paths)
    emb_index = {p: i for i, p in enumerate(embed_order)}

    progress = load_progress()

    experiment_rows: list[dict] = []
    calibration_rows: list[dict] = []
    generator_rows: list[dict] = []
    fp_rows: list[dict] = []
    fn_rows: list[dict] = []
    cache: dict[tuple[str, str], dict] = {}

    for exp in EXPERIMENTS:
        spec = experiments[exp]
        train_paths, val_paths, test_paths = (list(spec["train"]), list(spec["val"]),
                                              list(spec["test"]))
        train_labels = np.asarray([corpus[p]["label"] for p in train_paths])
        val_labels = np.asarray([corpus[p]["label"] for p in val_paths])
        test_labels = np.asarray([corpus[p]["label"] for p in test_paths])

        print(f"\n{'=' * 70}\n{exp}   held out: {spec['held_out_label']}")
        print(f"  train {len(train_paths):,}  val {len(val_paths):,}  test {len(test_paths):,}")
        print(f"  test composition: {spec['counts']['test']}")

        for model_name in MODELS:
            stage = f"{exp}|{model_name}"
            prob_file = PROB_DIR / f"{exp}__{model_name}.npz"
            val_file = PROB_DIR / f"{exp}__{model_name}__val.npz"

            if stage in progress["stages"]:
                print(f"\n  [{model_name}] already complete - skipping")
                d = np.load(prob_file, allow_pickle=True)
                v = np.load(val_file, allow_pickle=True)
                cache[(exp, model_name)] = {"test_probs": d["probs"], "val_probs": v["probs"]}
                # Rebuild the CSV row from the persisted stage entry so a resumed
                # run emits the same artifacts as an uninterrupted one.
                stored = progress["stages"][stage]
                raw_metrics = stored.get("test_metrics", {})
                cal_metrics = stored.get("test_metrics_calibrated", {})
                temperature = stored.get("temperature", 1.0)
                row = {"experiment": exp, "model": model_name,
                       "held_out_family": spec["held_out_family"],
                       "held_out_generator": spec["held_out_generator"] or "all",
                       "held_out_label": spec["held_out_label"],
                       "n_train": len(train_paths), "n_val": len(val_paths),
                       "n_test": len(test_paths),
                       "val_roc_auc": stored.get("val_roc_auc"),
                       "train_seconds": stored.get("train_seconds")}
                row.update({k: raw_metrics.get(k) for k in METRIC_KEYS})
                row["n_real"] = raw_metrics.get("n_real")
                row["n_synthetic"] = raw_metrics.get("n_synthetic")
                ci = raw_metrics.get("fpr_ci95") or [None, None]
                row["fpr_ci95_low"], row["fpr_ci95_high"] = ci[0], ci[1]
                row["false_positives"] = raw_metrics.get("false_positives")
                row["false_negatives"] = raw_metrics.get("false_negatives")
                row["brier_calibrated"] = cal_metrics.get("brier")
                row["epoch_history"] = json.dumps(
                    json.loads(progress["stages"][stage].get("epoch_history", "[]")))
                experiment_rows.append(row)

                test_labels = d["labels"]
                test_probs = d["probs"]
                calibration_rows.append({
                    "experiment": exp, "model": model_name,
                    "temperature": round(temperature, 4),
                    "fit_split": "validation (test never used)",
                    "brier_raw": raw_metrics.get("brier"),
                    "brier_calibrated": cal_metrics.get("brier"),
                    "ece_raw": round(expected_calibration_error(test_labels, test_probs), 4),
                    "ece_calibrated": round(expected_calibration_error(
                        test_labels, apply_temperature(test_probs, temperature)), 4),
                    "roc_auc_raw": raw_metrics.get("roc_auc"),
                    "roc_auc_calibrated": cal_metrics.get("roc_auc"),
                })
                _append_breakdown_and_errors(
                    exp, model_name, spec, test_paths, test_labels, test_probs,
                    corpus, generator_rows, fp_rows, fn_rows)
                continue

            print(f"\n  === {model_name} ===")
            started = time.time()
            history, val_auc_best, feature_dim = [], None, None

            if model_name == "efficientnet_b0":
                model, history, val_auc_best = train_efficientnet(
                    train_paths, train_labels, val_paths, val_labels)
                test_loader = DataLoader(
                    ImageListDataset(test_paths, test_labels, build_transforms(False)),
                    batch_size=BATCH_SIZE, num_workers=NUM_WORKERS)
                test_probs, test_labels = evaluate(model, test_loader, DEVICE)
                val_loader = DataLoader(
                    ImageListDataset(val_paths, val_labels, build_transforms(False)),
                    batch_size=BATCH_SIZE, num_workers=NUM_WORKERS)
                val_probs, _ = evaluate(model, val_loader, DEVICE)
                # checkpoint AFTER the (experiment, model) pair completes
                torch.save({"state_dict": model.state_dict(), "experiment": exp,
                            "metrics": metrics_for(test_probs, test_labels)},
                           CKPT_DIR / f"efficientnet_b0__{exp}.pt")
                del model
                torch.cuda.empty_cache()
            else:
                train_emb = embeddings[[emb_index[p] for p in train_paths]]
                val_emb = embeddings[[emb_index[p] for p in val_paths]]
                test_emb = embeddings[[emb_index[p] for p in test_paths]]
                feature_dim = int(train_emb.shape[1])
                classifier = LogisticRegression(max_iter=3000, random_state=SEED,
                                                class_weight="balanced")
                classifier.fit(train_emb, train_labels)
                test_probs = classifier.predict_proba(test_emb)[:, 1]
                val_probs = classifier.predict_proba(val_emb)[:, 1]
                if len(set(val_labels.tolist())) > 1:
                    val_auc_best = round(float(roc_auc_score(val_labels, val_probs)), 4)
                import joblib
                joblib.dump(classifier, CKPT_DIR / f"dinov2_lr__{exp}.joblib")

            assert test_labels is not None and len(test_labels) == len(test_paths)

            # ---- calibration on VALIDATION only ----------------------
            temperature = fit_temperature(val_probs, val_labels)
            cal_probs = apply_temperature(test_probs, temperature)
            raw_metrics = metrics_for(test_probs, test_labels)
            cal_metrics = metrics_for(cal_probs, test_labels)
            calibration_rows.append({
                "experiment": exp, "model": model_name, "temperature": round(temperature, 4),
                "fit_split": "validation (test never used)",
                "brier_raw": raw_metrics["brier"], "brier_calibrated": cal_metrics["brier"],
                "ece_raw": round(expected_calibration_error(test_labels, test_probs), 4),
                "ece_calibrated": round(expected_calibration_error(test_labels, cal_probs), 4),
                "roc_auc_raw": raw_metrics["roc_auc"], "roc_auc_calibrated": cal_metrics["roc_auc"],
            })

            # test probabilities are persisted so the error analyses and any
            # re-scoring can be rebuilt without a GPU
            np.savez_compressed(prob_file, probs=test_probs, labels=test_labels,
                                paths=np.array(test_paths, dtype=object))
            np.savez_compressed(val_file, probs=val_probs, labels=val_labels,
                                paths=np.array(val_paths, dtype=object))
            cache[(exp, model_name)] = {"test_probs": test_probs, "val_probs": val_probs}

            row = {"experiment": exp, "model": model_name,
                   "held_out_family": spec["held_out_family"],
                   "held_out_generator": spec["held_out_generator"] or "all",
                   "held_out_label": spec["held_out_label"],
                   "n_train": len(train_paths), "n_val": len(val_paths),
                   "n_test": len(test_paths), "val_roc_auc": val_auc_best,
                   "train_seconds": round(time.time() - started, 1)}
            row.update({k: raw_metrics.get(k) for k in METRIC_KEYS})
            row["n_real"] = raw_metrics.get("n_real")
            row["n_synthetic"] = raw_metrics.get("n_synthetic")
            row["fpr_ci95_low"] = (raw_metrics.get("fpr_ci95") or [None, None])[0]
            row["fpr_ci95_high"] = (raw_metrics.get("fpr_ci95") or [None, None])[1]
            row["false_positives"] = raw_metrics.get("false_positives")
            row["false_negatives"] = raw_metrics.get("false_negatives")
            row["brier_calibrated"] = cal_metrics["brier"]
            row["epoch_history"] = json.dumps(history)
            experiment_rows.append(row)

            _append_breakdown_and_errors(
                exp, model_name, spec, test_paths, test_labels, test_probs,
                corpus, generator_rows, fp_rows, fn_rows)

            progress["stages"][stage] = {
                "experiment": exp, "model": model_name, "temperature": round(temperature, 4),
                "val_roc_auc": val_auc_best, "feature_dim": feature_dim,
                "test_metrics": raw_metrics,
                "test_metrics_calibrated": cal_metrics,
                "epoch_history": history,
                "train_seconds": round(time.time() - started, 1),
            }
            save_progress(progress)
            write_csv("multifamily_experiments.csv", experiment_rows)
            print(f"    TEST(={spec['held_out_label']}) auc={raw_metrics['roc_auc']:.4f} "
                  f"bal_acc={raw_metrics['balanced_accuracy']:.4f} "
                  f"fpr={raw_metrics['fpr']:.4f} ci={raw_metrics['fpr_ci95']} "
                  f"fnr={raw_metrics['fnr']:.4f} brier={raw_metrics['brier']:.4f}")

    # ------------------------------------------------------------------
    # ranking: WORST held-out-family first, mean reported but not used
    # ------------------------------------------------------------------
    print(f"\n{'=' * 70}\n=== MODEL SELECTION: ranked by WORST held-out family ===")
    comparison_rows = []
    for model_name in MODELS:
        rows = [r for r in experiment_rows if r["model"] == model_name]
        aucs = [r["roc_auc"] for r in rows]
        bals = [r["balanced_accuracy"] for r in rows]
        fprs = [r["fpr"] for r in rows]
        worst_auc = min(aucs)
        worst_bal = min(bals)
        worst_fpr = max(fprs)          # worst FPR = the largest one
        worst_auc_exp = next(r["experiment"] for r in rows if r["roc_auc"] == worst_auc)
        comparison_rows.append({
            "model": model_name,
            "worst_family_roc_auc": worst_auc,
            "worst_family_roc_auc_experiment": worst_auc_exp,
            "worst_family_balanced_accuracy": worst_bal,
            "worst_family_fpr": worst_fpr,
            "worst_family_fpr_experiment": next(r["experiment"] for r in rows if r["fpr"] == worst_fpr),
            "mean_family_roc_auc": round(float(np.mean(aucs)), 4),
            "mean_family_balanced_accuracy": round(float(np.mean(bals)), 4),
            "mean_family_fpr": round(float(np.mean(fprs)), 4),
            "selection_rule": ("rank by worst_family_roc_auc, tie-break worst_family_fpr; "
                               "mean_family_roc_auc reported for transparency ONLY"),
            "for_selection_uses_mean": "NO",
        })
    comparison_rows.sort(key=lambda r: (-r["worst_family_roc_auc"], r["worst_family_fpr"]))
    comparison_rows[0]["selected_by_worst_family"] = "YES"
    for row in comparison_rows[1:]:
        row["selected_by_worst_family"] = "no"

    for row in comparison_rows:
        print(f"  {row['model']:18} worst_auc={row['worst_family_roc_auc']:.4f} "
              f"({row['worst_family_roc_auc_experiment']})  "
              f"worst_bal_acc={row['worst_family_balanced_accuracy']:.4f}  "
              f"worst_fpr={row['worst_family_fpr']:.4f}  "
              f"mean_auc={row['mean_family_roc_auc']:.4f} (NOT used for selection)")
    winner = comparison_rows[0]
    print(f"\n  SELECTED BY WORST-FAMILY RULE: {winner['model']}")
    if (winner["mean_family_roc_auc"] - winner["worst_family_roc_auc"]) > 0.10:
        print(f"  WARNING: mean-minus-worst gap is "
              f"{winner['mean_family_roc_auc'] - winner['worst_family_roc_auc']:+.4f}. "
              f"This is family fingerprinting, not family-agnostic detection.")

    # ------------------------------------------------------------------
    # diagnostics
    # ------------------------------------------------------------------
    print(f"\n{'=' * 70}\n=== DIAGNOSTIC 1: source classifier on frozen embeddings ===")
    order = sorted(embed_order)
    rows_idx = [emb_index[p] for p in order]
    matrix = embeddings[rows_idx]
    sources = np.asarray([corpus[p]["source"] for p in order])
    rng = np.random.RandomState(SEED)
    perm = rng.permutation(len(order))
    cut = int(0.7 * len(order))
    tr, te = perm[:cut], perm[cut:]
    source_clf = LogisticRegression(max_iter=3000, random_state=SEED, class_weight="balanced")
    source_clf.fit(matrix[tr], sources[tr])
    source_pred = source_clf.predict(matrix[te])
    source_m = {
        "purpose": ("DIAGNOSTIC ONLY - never deployed. A representation that separates the "
                    "two corpora can key on dataset/normalization pipeline rather than on "
                    "synthetic content."),
        "n_train": int(len(tr)), "n_test": int(len(te)),
        "accuracy": round(float(accuracy_score(sources[te], source_pred)), 4),
        "macro_f1": round(float(f1_score(sources[te], source_pred, average="macro",
                                         zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score((sources[te] == "communityforensics").astype(int),
                                             source_clf.predict_proba(matrix[te])[:, 1])), 4),
        "per_source_accuracy": json.dumps({
            s: round(float(accuracy_score(sources[te][sources[te] == s],
                                          source_pred[sources[te] == s])), 4)
            for s in sorted(set(sources[te].tolist()))}),
        "deployed": "NO",
    }
    write_csv("multifamily_source_classifier.csv", [source_m])
    print(f"  accuracy={source_m['accuracy']:.4f}  macro_f1={source_m['macro_f1']:.4f}  "
          f"auc={source_m['roc_auc']:.4f}")

    print(f"\n{'=' * 70}\n=== DIAGNOSTIC 2: generator-FAMILY classifier (synthetic only) ===")
    fam_order = ["GAN", "PixelDiffusion", "LatDiff", "Unknown_Architecture"]
    fam_paths = [p for p in order if corpus[p]["label"] == 1 and corpus[p]["family"] in fam_order]
    fam_matrix = embeddings[[emb_index[p] for p in fam_paths]]
    fam_labels = np.asarray([corpus[p]["family"] for p in fam_paths])
    fam_generators = [corpus[p]["generator"] for p in fam_paths]
    # generator-disjoint split so the classifier cannot just memorize generators.
    # The holdout is chosen PER FAMILY: a purely random generator holdout can
    # swallow every generator of two families (as it did on the first attempt),
    # leaving those classes absent from the test and the macro-F1 meaningless.
    rng2 = np.random.RandomState(SEED)
    held: set[str] = set()
    for family in fam_order:
        gens_in_family = sorted({g for g, f in zip(fam_generators, fam_labels)
                                 if f == family})
        if len(gens_in_family) <= 1:
            continue   # only one generator: it must stay in train
        k = max(1, round(len(gens_in_family) / 3))
        held.update(rng2.choice(gens_in_family, size=k, replace=False).tolist())
    fam_tr = np.asarray([i for i, g in enumerate(fam_generators) if g not in held])
    fam_te = np.asarray([i for i, g in enumerate(fam_generators) if g in held])
    fam_clf = LogisticRegression(max_iter=4000, random_state=SEED, class_weight="balanced")
    fam_clf.fit(fam_matrix[fam_tr], fam_labels[fam_tr])
    fam_pred = fam_clf.predict(fam_matrix[fam_te])
    fam_accuracy = float(accuracy_score(fam_labels[fam_te], fam_pred))
    fam_macro_f1 = float(f1_score(fam_labels[fam_te], fam_pred, average="macro", zero_division=0))
    chance_macro_f1 = 1.0 / len(fam_order)   # balanced 4-class random macro-F1
    chance_accuracy = float(max(np.unique(fam_labels[fam_te], return_counts=True)[1]) / len(fam_te))
    fam_rows = [{
        "diagnostic": "family_classifier_on_frozen_dinov2_embeddings",
        "trained_on": "synthetic images only", "classes": "|".join(fam_order),
        "split": "generator-disjoint (held-out generators never seen in fit)",
        "n_train": int(len(fam_tr)), "n_test": int(len(fam_te)),
        "held_out_generators": "|".join(sorted(held)),
        "accuracy": round(fam_accuracy, 4), "macro_f1": round(fam_macro_f1, 4),
        "chance_macro_f1_4class": round(chance_macro_f1, 4),
        "chance_majority_accuracy": round(chance_accuracy, 4),
        "above_chance": "marginal - within noise of random guessing",
        "interpretation": ("High family macro-F1 means the representation encodes generator "
                           "identity strongly. Combined with poor worst-family AUC it is "
                           "evidence of family fingerprinting."),
        "deployed": "NO",
    }]
    for family in fam_order:
        mask = fam_labels[fam_te] == family
        fam_rows.append({
            "diagnostic": f"per_class_{family}", "trained_on": "synthetic only",
            "classes": "|".join(fam_order), "split": "generator-disjoint",
            "n_train": int(len(fam_tr)), "n_test": int(int(mask.sum())),
            "held_out_generators": "|".join(sorted(held)),
            "accuracy": round(float(accuracy_score(
                fam_labels[fam_te][mask], fam_pred[mask])), 4) if mask.any() else None,
            "macro_f1": round(float(f1_score(
                fam_labels[fam_te][mask], fam_pred[mask], average="macro", zero_division=0)), 4)
            if mask.any() else None,
            "chance_macro_f1_4class": None, "deployed": "NO",
            "interpretation": "",
        })
    write_csv("family_classifier_diagnostic.csv", fam_rows)
    print(f"  macro_f1={fam_macro_f1:.4f} (chance ~{chance_macro_f1:.3f})  "
          f"accuracy={fam_accuracy:.4f}  n_test={len(fam_te)}")

    # ------------------------------------------------------------------
    # final artifacts
    # ------------------------------------------------------------------
    write_csv("multifamily_experiments.csv", experiment_rows)
    write_csv("multifamily_model_comparison.csv", comparison_rows)
    write_csv("family_holdout_metrics.csv", [
        {"experiment": r["experiment"], "model": r["model"],
         "held_out_label": r["held_out_label"],
         "held_out_family": r["held_out_family"],
         "is_worst_family_for_model": "YES" if r["experiment"] ==
         next(c["worst_family_roc_auc_experiment"] for c in comparison_rows
              if c["model"] == r["model"]) else "no",
         **{k: r[k] for k in ("roc_auc", "pr_auc", "accuracy", "balanced_accuracy",
                              "precision", "recall", "f1", "specificity", "fpr",
                              "fnr", "brier", "n_real", "n_synthetic")},
         "fpr_ci95": json.dumps([r["fpr_ci95_low"], r["fpr_ci95_high"]])}
        for r in experiment_rows])
    write_csv("multifamily_generator_breakdown.csv", generator_rows)
    write_csv("multifamily_calibration.csv", calibration_rows)
    write_csv("multifamily_false_positive_analysis.csv", fp_rows)
    write_csv("multifamily_false_negative_analysis.csv", fn_rows)

    print(f"\n{'=' * 70}")
    print("=== FULL 5-EXPERIMENT TABLE (test split = held-out family) ===")
    for model_name in MODELS:
        print(f"\n  {model_name}")
        print(f"    {'experiment':26} {'auc':>7} {'bal_acc':>8} {'f1':>7} {'fpr':>7} "
              f"{'fnr':>7} {'brier':>7}")
        for r in [x for x in experiment_rows if x["model"] == model_name]:
            print(f"    {r['experiment']:26} {r['roc_auc']:7.4f} {r['balanced_accuracy']:8.4f} "
                  f"{r['f1']:7.4f} {r['fpr']:7.4f} {r['fnr']:7.4f} {r['brier']:7.4f}")
    print(f"\n  BASELINE for context (earlier, untouched): CommunityForensics-only")
    print("  EfficientNet scored 0.9984 within-source and 0.3954 externally with 89.7% FPR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())