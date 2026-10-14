"""
Phase 3 robustness / calibration / uncertainty evaluation for the selected
multi-family EfficientNet-B0 candidate.

MODEL UNDER TEST (already trained, NOT retrained here):
  models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt
Experiment C_holdout_Midjourney: trained on GAN + PixelDiffusion + LatDiff,
tested against Midjourney (Unknown_Architecture) - a wholly unseen family.
Reported baseline: ROC-AUC 0.9832, balanced accuracy 0.9311, FPR 0.1109,
FNR 0.0269.

WHAT THIS SCRIPT ANSWERS
-------------------------
Does the model stay STABLE under transformations that a real deployment
will inevitably apply (JPEG recompression, downscaling, web-style handling)?
Robustness is NOT generalisation. A model can be perfectly stable and still
fail on an unseen generator family - and that is exactly the open blocker.

CONDITIONS
----------
  none                unperturbed reference
  jpeg_q95/85/70/50   recompression at four qualities
  res_512/256/128     downscale then resize back through the production pipeline
  web_512_jpeg85      original -> resize 512 -> JPEG q85 -> model input
                       (what a social platform / messaging app actually does)

Every transformation is applied SYMMETRICALLY to real and synthetic images.
No class-conditional handling anywhere in this file.

SPLITS
------
  TEST split of C_holdout_Midjourney  -> the only images used for the
      headline robustness numbers. Contains 1290 real + 260 Midjourney.
  VAL split                            -> calibrator fitting, threshold
      selection, and the per-family probe set. Never scored as a headline.

PER-FAMILY PROBE (and its honest limitation)
--------------------------------------------
The C test split contains only real + Midjourney, so it cannot produce a
per-family robustness breakdown on its own. The breakdown therefore uses the
VAL split's synthetic images grouped by family (GAN / PixelDiffusion /
LatDiff / Unknown_Architecture=Val-pool-Midjourney-excluded) against the
held-out TEST real pool. Those three families were SEEN in training, so their
numbers are optimistic relative to the unseen Midjourney family. The
breakdown answers "does a transform disproportionately hurt family X",
not "does family X generalize". This is stated in the CSVs themselves.

STANDING LIMITATION CARRIED THROUGH EVERY NUMBER
------------------------------------------------
The source classifier on the frozen representation reaches ROC-AUC 0.9709:
the learned representation largely encodes WHICH CORPUS an image came from
rather than synthetic content. Every robustness figure below inherits that
confound - a transform that perturbs corpus-specific fingerprint features will
look like a content robustness failure. Nothing here attempts to fix it.

HARD RULES ENFORCED
-------------------
* No training, no refitting, on transformed or test images. Fitting happens on
  the validation split only, and only for calibrators and thresholds.
* TEST images are measured once and reported, never used to choose anything.
* num_workers=4 on every DataLoader.
* Single GPU job. 4GB VRAM previously OOMed on two concurrent jobs.
* Writes only under results/phase3/. Touches nothing in app/, nothing in
  models/ACTIVE_MODEL.json, no ACTIVE_IMAGE_MODEL.json.
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
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    roc_auc_score,
)
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
RESULTS = BACKEND / "results" / "phase3"
SPLITS = RESULTS / "multifamily_splits.json"
CORPUS = RESULTS / "multifamily_corpus.csv"
CKPT = BACKEND / "models" / "multifamily_candidates" / "efficientnet_b0__C_holdout_Midjourney.pt"
PROB_CACHE = RESULTS / "robustness_probs_cache.npz"
SUMMARY = RESULTS / "robustness_summary.json"

EXPERIMENT = "C_holdout_Midjourney"
FAMILY_ORDER = ["GAN", "PixelDiffusion", "LatDiff", "Unknown_Architecture"]

SEED = 42
BATCH_SIZE = 32
IMAGE_SIZE = 224          # production MODEL_INPUT_SIZE (app/image/preprocessing.py)
NUM_WORKERS = 4
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

SOURCE_BIAS_CAVEAT = (
    "CONFOUND: source classifier on the frozen representation reaches ROC-AUC 0.9709 - "
    "the representation largely encodes which corpus an image came from. Every "
    "robustness number inherits this confound."
)
GENERALISATION_CAVEAT = (
    "Robustness is NOT generalisation. This model is stable-or-not under transforms; "
    "it is separately blocked on worst-family generalisation (GAN balanced accuracy 0.5512)."
)

CONDITIONS: dict[str, dict] = {
    "none": {"group": "none", "desc": "unperturbed reference"},
    "jpeg_q95": {"group": "jpeg", "desc": "JPEG recompression quality 95"},
    "jpeg_q85": {"group": "jpeg", "desc": "JPEG recompression quality 85"},
    "jpeg_q70": {"group": "jpeg", "desc": "JPEG recompression quality 70"},
    "jpeg_q50": {"group": "jpeg", "desc": "JPEG recompression quality 50"},
    "res_512": {"group": "resolution", "desc": "downscale to 512x512, then production resize"},
    "res_256": {"group": "resolution", "desc": "downscale to 256x256, then production resize"},
    "res_128": {"group": "resolution", "desc": "downscale to 128x128, then production resize"},
    "web_512_jpeg85": {"group": "web", "desc": "resize 512 -> JPEG q85 -> model input"},
}


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------
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


def nll(labels: np.ndarray, probs: np.ndarray) -> float:
    p = np.clip(probs, 1e-7, 1 - 1e-7)
    return float(-np.mean(labels * np.log(p) + (1 - labels) * np.log(1 - p)))


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path = RESULTS / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  written: {path.name}  ({len(rows)} rows)")


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------
METRIC_KEYS = ("roc_auc", "pr_auc", "balanced_accuracy", "fpr", "fnr",
               "accuracy", "brier", "ece", "nll")


def metrics_for(probs: np.ndarray, labels: np.ndarray, threshold: float = 0.5) -> dict:
    if len(labels) == 0:
        return {"n": 0, "note": "empty subset"}
    n_real = int((labels == 0).sum())
    n_syn = int((labels == 1).sum())
    if n_real == 0 or n_syn == 0:
        # single class: AUC is undefined, report counts only
        preds = (probs >= threshold).astype(int)
        return {"n": int(len(labels)), "n_real": n_real, "n_synthetic": n_syn,
                "roc_auc": None, "pr_auc": None, "balanced_accuracy": None,
                "accuracy": round(float(accuracy_score(labels, preds)), 4),
                "fpr": None, "fnr": None, "note": "single class - AUC undefined"}
    preds = (probs >= threshold).astype(int)
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
        "fpr": round(fp / n_real, 4),
        "fpr_ci95_low": round(lo, 4),
        "fpr_ci95_high": round(hi, 4),
        "fnr": round(fn / n_syn, 4),
        "brier": round(float(brier_score_loss(labels, probs)), 4),
        "ece": round(expected_calibration_error(labels, probs), 4),
        "nll": round(nll(labels, probs), 4),
        "false_positives": fp,
        "false_negatives": fn,
        "mean_probability": round(float(probs.mean()), 4),
    }


# --------------------------------------------------------------------------
# transformations - applied identically to every image regardless of class
# --------------------------------------------------------------------------
def apply_transform(image: Image.Image, condition: str) -> Image.Image:
    image = image.convert("RGB")
    if condition == "none":
        return image
    if condition.startswith("jpeg_q"):
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=int(condition.split("q")[1]),
                  subsampling=0)   # 4:4:4, the default a web platform would not always use
        buffer.seek(0)
        return Image.open(buffer).convert("RGB")
    if condition.startswith("res_"):
        size = int(condition.split("_")[1])
        return image.resize((size, size), Image.BICUBIC)
    if condition == "web_512_jpeg85":
        image = image.resize((512, 512), Image.BICUBIC)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85, subsampling=0)
        buffer.seek(0)
        return Image.open(buffer).convert("RGB")
    raise ValueError(f"unknown condition {condition}")


# production inference pipeline: resize to 224, tensor, imagenet normalise
FINAL_TRANSFORM = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


class ConditionDataset(Dataset):
    """Loads the ORIGINAL image, applies the condition, then the production
    pipeline. Identical code path for real and synthetic."""

    def __init__(self, paths, labels, condition):
        self.paths, self.labels, self.condition = list(paths), labels, condition

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        try:
            with Image.open(PROJECT / self.paths[index]) as handle:
                image = handle.convert("RGB")
        except Exception:  # noqa: BLE001
            image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))
        image = apply_transform(image, self.condition)
        return FINAL_TRANSFORM(image), int(self.labels[index])


def build_model() -> nn.Module:
    model = models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    checkpoint = torch.load(CKPT, map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    model.to(DEVICE).eval()
    return model, checkpoint


def predict(model: nn.Module, paths, labels, condition: str) -> np.ndarray:
    loader = DataLoader(ConditionDataset(paths, labels, condition),
                        batch_size=BATCH_SIZE, num_workers=NUM_WORKERS)
    probs = []
    with torch.no_grad():
        for images, _ in loader:
            logits = model(images.to(DEVICE))
            probs.extend(torch.softmax(logits, 1)[:, 1].cpu().numpy().tolist())
    return np.asarray(probs, dtype=np.float64)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load_corpus() -> dict[str, dict]:
    rows = csv.DictReader(CORPUS.open(encoding="utf-8"))
    return {r["path"]: {"label": int(r["label"]), "source": r["source"],
                        "family": r["family"], "generator": r["generator"]}
            for r in rows}


def family_probe_sets(corpus: dict[str, dict], spec: dict) -> dict[str, dict]:
    """Per-family synthetic probe, each scored against the held-out TEST real pool.

    GAN / PixelDiffusion / LatDiff come from the VALIDATION split (never trained
    on, but the families themselves were seen in training, so those rows are
    optimistic). Unknown_Architecture = Midjourney exists ONLY in the test split,
    so it is taken from there - which is the correct source for it, since it is
    the genuinely held-out family and the test split is where measurement is
    supposed to happen. It is measured, never fit.
    """
    test_real = [p for p in spec["test"] if corpus[p]["label"] == 0]
    families: dict[str, dict] = {}
    families["real"] = {"paths": test_real, "labels": [0] * len(test_real),
                        "note": "held-out test real pool (identical across families)"}
    for family in FAMILY_ORDER:
        held_out = family == "Unknown_Architecture"
        source = "test" if held_out else "val"
        pool = spec["test"] if held_out else spec["val"]
        paths = [p for p in pool
                 if corpus[p]["label"] == 1 and corpus[p]["family"] == family]
        if not paths:
            print(f"  WARNING: no {family} images found in the {source} split")
            continue
        combined = test_real + paths
        families[family] = {
            "paths": combined,
            "labels": [0] * len(test_real) + [1] * len(paths),
            "synthetic_only": paths,
            "probe_split": source,
            "note": ("held-out family - never seen in training; measured on the test split"
                     if held_out else
                     "family seen in training (probe is val-split synthetic): optimistic"),
        }
    return families


# --------------------------------------------------------------------------
# calibrators - FIT ON VALIDATION ONLY
# --------------------------------------------------------------------------
def fit_temperature(val_probs: np.ndarray, val_labels: np.ndarray) -> float:
    logits = np.log(np.clip(val_probs, 1e-6, 1 - 1e-6) /
                    np.clip(1 - val_probs, 1e-6, 1 - 1e-6))
    grid = np.linspace(np.log(0.05), np.log(20.0), 121)

    def loss_for(log_t: float) -> float:
        scaled = np.clip(logits / np.exp(log_t), -60.0, 60.0)
        return float(-np.mean(val_labels * -np.logaddexp(0.0, -scaled)
                              + (1 - val_labels) * -np.logaddexp(0.0, scaled)))

    best_t, best_loss = 1.0, float("inf")
    for log_t in grid:
        value = loss_for(log_t)
        if value < best_loss:
            best_t, best_loss = float(np.exp(log_t)), value
    return best_t


def apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
    logits = np.log(np.clip(probs, 1e-6, 1 - 1e-6) /
                    np.clip(1 - probs, 1e-6, 1 - 1e-6)) / temperature
    return 1.0 / (1.0 + np.exp(-logits))


def fit_platt(val_probs: np.ndarray, val_labels: np.ndarray):
    logits = np.log(np.clip(val_probs, 1e-6, 1 - 1e-6) /
                    np.clip(1 - val_probs, 1e-6, 1 - 1e-6)).reshape(-1, 1)
    model = LogisticRegression(max_iter=3000, random_state=SEED)
    model.fit(logits, val_labels)
    return float(model.coef_[0][0]), float(model.intercept_[0])


def apply_platt(probs: np.ndarray, a: float, b: float) -> np.ndarray:
    logits = np.log(np.clip(probs, 1e-6, 1 - 1e-6) /
                    np.clip(1 - probs, 1e-6, 1 - 1e-6))
    return 1.0 / (1.0 + np.exp(-(a * logits + b)))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"device: {DEVICE}; torch {torch.__version__}")
    print(f"checkpoint: {CKPT.name}")
    print(SOURCE_BIAS_CAVEAT)
    print(GENERALISATION_CAVEAT)

    corpus = load_corpus()
    spec = json.loads(SPLITS.read_text(encoding="utf-8"))["experiments"][EXPERIMENT]
    test_paths = list(spec["test"])
    test_labels = np.asarray([corpus[p]["label"] for p in test_paths])
    val_paths = list(spec["val"])
    val_labels = np.asarray([corpus[p]["label"] for p in val_paths])
    probe = family_probe_sets(corpus, spec)
    print(f"test {len(test_paths):,}  val {len(val_paths):,}  "
          f"probe families: { {k: len(v['paths']) for k, v in probe.items()} }")

    model, checkpoint = build_model()
    model_size_mb = CKPT.stat().st_size / (1024 * 1024)

    # ----------------------------------------------------------------
    # 1. probability collection (cached so re-runs are free)
    # ----------------------------------------------------------------
    cache: dict[str, np.ndarray] = {}
    if PROB_CACHE.exists():
        try:
            with np.load(PROB_CACHE, allow_pickle=True) as data:
                cache = {k: data[k] for k in data.files}
            print(f"  probability cache hit ({len(cache)} arrays)")
        except Exception:  # noqa: BLE001
            cache = {}

    def flush_cache() -> None:
        """Persist after every condition so a long run resumes instead of
        restarting: a full sweep is ~45k image inferences on one GPU."""
        with PROB_CACHE.open("wb") as handle:
            np.savez_compressed(handle, **cache)

    def probs_for(key: str, paths, labels, condition: str) -> np.ndarray:
        if key in cache and len(cache[key]) == len(paths):
            print(f"    {key:46} n={len(paths):5d}  cached", flush=True)
            return cache[key]
        started = time.time()
        values = predict(model, paths, labels, condition)
        cache[key] = values
        print(f"    {key:46} n={len(values):5d}  {time.time() - started:5.1f}s", flush=True)
        flush_cache()
        return values

    print(f"\n=== TEST-split probabilities across {len(CONDITIONS)} conditions ===")
    test_probs = {c: probs_for(f"test__{c}", test_paths, test_labels, c) for c in CONDITIONS}
    print("=== VALIDATION probabilities (unperturbed + worst transforms) ===")
    val_probs = {c: probs_for(f"val__{c}", val_paths, val_labels, c)
                 for c in ("none", "jpeg_q50", "res_128", "web_512_jpeg85")}
    print("=== FAMILY PROBE probabilities ===")
    probe_probs = {family: {c: probs_for(f"probe__{family}__{c}", data["paths"],
                                          data["labels"], c)
                            for c in CONDITIONS}
                   for family, data in probe.items()}
    print(f"  probability cache saved: {PROB_CACHE.name}")

    base_probs = test_probs["none"]
    base_pred = (base_probs >= 0.5).astype(int)

    # ----------------------------------------------------------------
    # 2. JPEG / resolution / web tables
    # ----------------------------------------------------------------
    group_outputs = {
        "jpeg": ("jpeg_robustness.csv",
                 ["none"] + [c for c in CONDITIONS if c.startswith("jpeg_q")]),
        "resolution": ("resolution_robustness.csv",
                       ["none"] + [c for c in CONDITIONS if c.startswith("res_")]),
        "web": ("web_transform_robustness.csv", ["none", "web_512_jpeg85"]),
    }
    summary: dict = {"source_bias_caveat": SOURCE_BIAS_CAVEAT,
                     "generalisation_caveat": GENERALISATION_CAVEAT,
                     "model": CKPT.name, "experiment": EXPERIMENT}

    group_tables: dict[str, list[dict]] = {}
    for group, (filename, keys) in group_outputs.items():
        rows = []
        for condition in keys:
            values = test_probs[condition]
            m = metrics_for(values, test_labels)
            preds = (values >= 0.5).astype(int)
            shifted = int(((base_pred == 0) & (preds == 1)).sum())
            recovered = int(((base_pred == 1) & (preds == 0)).sum())
            rows.append({
                "condition": condition,
                "description": CONDITIONS[condition]["desc"],
                **m,
                "mean_probability_shift": round(float(np.mean(values - base_probs)), 4),
                "mean_abs_probability_shift": round(float(np.mean(np.abs(values - base_probs))), 4),
                "predictions_flipped_real_to_synthetic": shifted if condition != "none" else 0,
                "predictions_flipped_synthetic_to_real": recovered if condition != "none" else 0,
                "source_bias_caveat": SOURCE_BIAS_CAVEAT,
            })
        group_tables[group] = rows
        write_csv(filename, rows)
        summary[group] = [{k: r[k] for k in
                           ("condition", "roc_auc", "pr_auc", "balanced_accuracy",
                            "fpr", "fnr", "brier", "mean_probability_shift")} for r in rows]

    # ----------------------------------------------------------------
    # 3. per-family robustness breakdown
    # ----------------------------------------------------------------
    family_rows = []
    for family, data in probe.items():
        if family == "real":
            # the real pool alone has no AUC; report its flip behaviour only
            continue
        base = probe_probs[family]["none"]
        for condition in CONDITIONS:
            values = probe_probs[family][condition]
            m = metrics_for(values, np.asarray(data["labels"]))
            base_p = (base >= 0.5).astype(int)
            preds = (values >= 0.5).astype(int)
            family_rows.append({
                "family": family,
                "condition": condition,
                "description": CONDITIONS[condition]["desc"],
                "seen_in_training": "NO - held out" if family == "Unknown_Architecture" else "yes",
                "probe_source": (f"{data.get('probe_split', 'val')} split synthetic "
                                "vs held-out test real pool"),
                **m,
                "delta_balanced_accuracy_vs_none": None,
                "delta_fpr_vs_none": None,
                "flips_real_to_synthetic": 0 if condition == "none" else
                    int(((base_p == 0) & (preds == 1)).sum()),
                "flips_synthetic_to_real": 0 if condition == "none" else
                    int(((base_p == 1) & (preds == 0)).sum()),
                "note": data["note"],
                "source_bias_caveat": SOURCE_BIAS_CAVEAT,
            })
    for family in FAMILY_ORDER:
        subset = [r for r in family_rows if r["family"] == family]
        if not subset:
            continue
        base_row = next(r for r in subset if r["condition"] == "none")
        for row in subset:
            if row["balanced_accuracy"] is not None and base_row["balanced_accuracy"] is not None:
                row["delta_balanced_accuracy_vs_none"] = round(
                    row["balanced_accuracy"] - base_row["balanced_accuracy"], 4)
            if row["fpr"] is not None and base_row["fpr"] is not None:
                row["delta_fpr_vs_none"] = round(row["fpr"] - base_row["fpr"], 4)
    write_csv("robustness_by_family.csv", family_rows)
    summary["by_family"] = [
        {"family": f,
         "seen_in_training": "NO" if f == "Unknown_Architecture" else "yes",
         **{c: next((r for r in family_rows
                     if r["family"] == f and r["condition"] == c), {}).get(k)
            for c in ("none", "jpeg_q70", "jpeg_q50", "res_128", "web_512_jpeg85")
            for k in ("balanced_accuracy", "fpr", "roc_auc", "delta_balanced_accuracy_vs_none")}}
        for f in FAMILY_ORDER]

    # ----------------------------------------------------------------
    # 4. calibration: RAW vs temperature vs Platt, fit on VALIDATION only
    # ----------------------------------------------------------------
    temperature = fit_temperature(val_probs["none"], val_labels)
    platt_a, platt_b = fit_platt(val_probs["none"], val_labels)
    val_variant = {
        "raw": val_probs["none"],
        "temperature": apply_temperature(val_probs["none"], temperature),
        "platt": apply_platt(val_probs["none"], platt_a, platt_b),
    }
    test_variant = {
        "raw": base_probs,
        "temperature": apply_temperature(base_probs, temperature),
        "platt": apply_platt(base_probs, platt_a, platt_b),
    }

    calib_rows = []
    calib_detail = {}
    for variant in ("raw", "temperature", "platt"):
        tv, vv = test_variant[variant], val_variant[variant]
        tm, vm = metrics_for(tv, test_labels), metrics_for(vv, val_labels)
        # transfer behaviour: the worst family's balanced accuracy under the
        # calibrated scores. Each probe set has its own image list, so its
        # probabilities must come from probe_probs - indexing the test vector
        # here would silently mix splits.
        worst_bal, worst_family = None, None
        for family, data in probe.items():
            if family == "real":
                continue
            labels = np.asarray(data["labels"])
            probe_base = probe_probs[family]["none"]
            pv = {"raw": probe_base,
                  "temperature": apply_temperature(probe_base, temperature),
                  "platt": apply_platt(probe_base, platt_a, platt_b)}[variant]
            cm = metrics_for(pv, labels)
            if cm.get("balanced_accuracy") is not None:
                if worst_bal is None or cm["balanced_accuracy"] < worst_bal:
                    worst_bal, worst_family = cm["balanced_accuracy"], family
        spread = float(np.std(tv))
        # monotonicity check: Spearman between raw and calibrated test scores
        order_raw = np.argsort(np.argsort(base_probs))
        order_cal = np.argsort(np.argsort(tv))
        rank_preserved = float(np.corrcoef(order_raw, order_cal)[0, 1])
        calib_rows.append({
            "method": variant,
            "fit_split": "VALIDATION only (test and held-out families never used for fitting)",
            "temperature": round(temperature, 4) if variant == "temperature" else "",
            "platt_slope": round(platt_a, 4) if variant == "platt" else "",
            "platt_intercept": round(platt_b, 4) if variant == "platt" else "",
            "val_brier": vm.get("brier"), "val_ece": vm.get("ece"), "val_nll": vm.get("nll"),
            **{f"test_{k}": tm.get(k) for k in METRIC_KEYS},
            "score_spread_std": round(spread, 4),
            "rank_preservation_vs_raw": round(rank_preserved, 6),
            "worst_family_balanced_accuracy": None if worst_bal is None else round(worst_bal, 4),
            "worst_family": worst_family,
            "source_bias_caveat": SOURCE_BIAS_CAVEAT,
        })
        calib_detail[variant] = {"test_probs": tv, "metrics": tm,
                                 "worst_bal": worst_bal, "worst_family": worst_family}
    write_csv("calibration_results.csv", calib_rows)

    # selection rule, applied mechanically
    base_auc = calib_detail["raw"]["metrics"]["roc_auc"]
    base_worst = calib_detail["raw"]["worst_bal"]
    decisions = {}
    for variant in ("temperature", "platt"):
        d = calib_detail[variant]
        rank_ok = abs(d["metrics"]["roc_auc"] - base_auc) < 1e-6
        worst_delta = None if (d["worst_bal"] is None or base_worst is None) else \
            d["worst_bal"] - base_worst
        spread_ok = float(np.std(test_variant[variant])) >= 0.5 * float(np.std(base_probs))
        transfer_ok = worst_delta is not None and worst_delta >= -0.01
        brier_gain = calib_detail["raw"]["metrics"]["brier"] - d["metrics"]["brier"]
        decisions[variant] = {
            "brier_improvement": round(brier_gain, 4),
            "roc_auc_preserved": bool(rank_ok),
            "worst_family_delta_balanced_accuracy": None if worst_delta is None else round(worst_delta, 4),
            "worst_family_stable": bool(transfer_ok),
            "score_spread_not_collapsed": bool(spread_ok),
            "accepted": bool(rank_ok and transfer_ok and spread_ok and brier_gain > 0),
        }
    print("\n=== calibration decisions ===")
    for variant, d in decisions.items():
        print(f"  {variant:12} {d}")
    summary["calibration_decisions"] = decisions
    summary["temperature"] = round(temperature, 4)
    summary["platt"] = {"slope": round(platt_a, 4), "intercept": round(platt_b, 4)}

    accepted = [v for v, d in decisions.items() if d["accepted"]]
    chosen = accepted[0] if accepted else "raw"
    print(f"  SELECTED CALIBRATION: {chosen}")

    # ----------------------------------------------------------------
    # 5. uncertainty policy - thresholds from VALIDATION data only
    # ----------------------------------------------------------------
    v_prob = val_variant[chosen]
    v_label = val_labels
    v_err = ((v_prob >= 0.5).astype(int) != v_label)
    confidence = np.abs(v_prob - 0.5)
    order = np.argsort(-confidence)
    # The two thresholds are chosen INDEPENDENTLY, one per side, each as the
    # widest band (lowest threshold) that still holds validation error at or
    # below target on that side.
    #
    # A single symmetric |p - 0.5| band cannot work here: the test split is
    # 1290 real vs 260 synthetic, so a confidence-ranked symmetric band fills up
    # with easy real images first and the synthetic side ends up empty. That is a
    # property of the class ratio, not of the detector, so forcing one symmetric
    # band would report an artificially tiny confident region.
    TARGET_ERR = 0.05
    MIN_REGION = 25          # never certify fewer images than this on validation

    def threshold_for_side(is_synthetic: bool, target: float) -> dict:
        """Pick the LOOSEST threshold whose validation region still meets the
        error target.

        For the real side the region {p < t} grows as t rises, so the loosest
        admissible t is the largest one that still qualifies. For the synthetic
        side {p > t} shrinks as t rises, so the loosest admissible t is the
        smallest qualifying one. Region error is NOT monotonic in t, so every
        threshold on the grid is scored and the extreme admissible value is
        taken - bailing out on the first failure would return an empty region
        while tighter thresholds are in fact still valid.
        """
        side_label = 1 if is_synthetic else 0
        side_probs = v_prob[v_label == side_label]
        side_error_rate = float(((side_probs >= 0.5).astype(int) != side_label).mean())
        admissible = []
        for candidate in np.arange(0.5, 0.999, 0.001):
            mask = (v_prob > candidate) if is_synthetic else (v_prob < candidate)
            count = int(mask.sum())
            if count < MIN_REGION:
                continue
            error = float(v_err[mask].mean())
            if error <= target:
                admissible.append({"threshold": round(float(candidate), 4), "n": count,
                                   "error": round(error, 4)})
        if not admissible:
            # The target is unreachable on this side. Report the best achievable
            # region instead of mislabelling: the loosest threshold minimising
            # validation region error, tie-broken towards wider coverage. The
            # caller records that the target was NOT met, so a reader can never
            # mistake this region for a certified 5%-error one.
            fallback = None
            for candidate in np.arange(0.5, 0.999, 0.001):
                mask = (v_prob > candidate) if is_synthetic else (v_prob < candidate)
                count = int(mask.sum())
                if count < MIN_REGION:
                    continue
                error = float(v_err[mask].mean())
                key = (round(error, 6), count)
                if fallback is None or key < (fallback[0], fallback[1]):
                    fallback = (error, count, round(float(candidate), 4))
            if fallback is None:
                return {"threshold": 0.5, "n": 0, "error": None,
                        "side_error_rate": round(side_error_rate, 4),
                        "target_met": False,
                        "note": (f"no threshold with >= {MIN_REGION} validation images on "
                                 f"this side; region is empty")}
            return {"threshold": fallback[2], "n": fallback[1],
                    "error": round(fallback[0], 4),
                    "side_error_rate": round(side_error_rate, 4),
                    "target_met": False,
                    "note": (f"TARGET NOT MET: no threshold reaches <= {target:.0%} "
                             f"validation error on this side. Reporting the best achievable "
                             f"region ({fallback[0]:.2%} error). Do not read this as a "
                             f"certified low-error region.")}
        # loosest threshold = widest region: the real side's region {p < t} grows
        # with t, the synthetic side's {p > t} shrinks with it.
        best = dict(max(admissible, key=lambda r: r["n"]))
        best["side_error_rate"] = round(side_error_rate, 4)
        best["n_admissible_thresholds"] = len(admissible)
        best["target_met"] = True
        return best

    real_side = threshold_for_side(False, TARGET_ERR)
    syn_side = threshold_for_side(True, TARGET_ERR)
    lower_t, upper_t = real_side["threshold"], syn_side["threshold"]
    policy = {
        "lower_threshold": lower_t,
        "upper_threshold": upper_t,
        "target_validation_error": TARGET_ERR,
        "min_region_size": MIN_REGION,
        "thresholds_source": ("chosen on VALIDATION only, each side independently; "
                               "not arbitrary 0.5"),
        "lower_side": real_side,
        "upper_side": syn_side,
        "validation_confident_coverage": round(
            (int((v_prob < lower_t).sum()) + int((v_prob > upper_t).sum())) / len(v_prob), 4),
    }

    def regions(probs: np.ndarray) -> dict:
        real = probs < lower_t
        syn = probs > upper_t
        uncertain = ~(real | syn)
        return {"LIKELY_REAL": real, "LIKELY_SYNTHETIC": syn, "UNCERTAIN": uncertain}

    unc_rows = []
    for split_name, probs, labels in (("validation", v_prob, v_label),
                                      ("test", test_variant[chosen], test_labels)):
        region_masks = regions(probs)
        n = len(labels)
        for region in ("LIKELY_REAL", "UNCERTAIN", "LIKELY_SYNTHETIC"):
            mask = region_masks[region]
            count = int(mask.sum())
            entry = {
                "region": region,
                "split": split_name,
                "thresholds_source": f"chosen on VALIDATION (target error <= {TARGET_ERR:.0%}, per side)",
                "lower_threshold": lower_t if split_name == "validation" else "",
                "upper_threshold": upper_t if split_name == "validation" else "",
                "lower_side_target_met": real_side.get("target_met") if split_name == "validation" else "",
                "upper_side_target_met": syn_side.get("target_met") if split_name == "validation" else "",
                "validation_error_in_this_region": (real_side.get("error") if region == "LIKELY_REAL"
                                                    else syn_side.get("error") if region == "LIKELY_SYNTHETIC"
                                                    else None) if split_name == "validation" else None,
                "n": count,
                "coverage": round(count / n, 4),
                "accuracy_in_region": round(float(((probs[mask] >= 0.5).astype(int)
                                                  == labels[mask]).mean()), 4) if count else None,
                "observed_error_in_region": round(float(1 - ((probs[mask] >= 0.5).astype(int)
                                                            == labels[mask]).mean()), 4) if count else None,
                "mean_probability": round(float(probs[mask].mean()), 4) if count else None,
                "uncertainty_rate": round(float(region_masks["UNCERTAIN"].sum() / n), 4)
                    if region == "UNCERTAIN" else None,
                "calibration_method": chosen,
                "source_bias_caveat": SOURCE_BIAS_CAVEAT,
            }
            unc_rows.append(entry)
    write_csv("uncertainty_policy.csv", unc_rows)
    summary["uncertainty_policy"] = policy
    summary["uncertainty_regions"] = [r for r in unc_rows if r["split"] == "test"]

    test_regions = regions(test_variant[chosen])
    confident = test_regions["LIKELY_REAL"] | test_regions["LIKELY_SYNTHETIC"]
    confident_error = float(1 - ((test_variant[chosen][confident] >= 0.5).astype(int)
                                 == test_labels[confident]).mean()) if confident.any() else None
    overall_error = float(1 - accuracy_score(test_labels,
                                             (test_variant[chosen] >= 0.5).astype(int)))
    high_confidence_error_lower = (confident_error is not None and confident_error < overall_error)
    print(f"\n=== uncertainty policy ===\n  thresholds: p<{lower_t} LIKELY_REAL, "
          f"{lower_t}<=p<={upper_t} UNCERTAIN, p>{upper_t} LIKELY_SYNTHETIC")
    print(f"  test uncertainty rate: {test_regions['UNCERTAIN'].mean():.4f}")
    print(f"  overall test error {overall_error:.4f} vs confident-region error "
          f"{confident_error:.4f} -> high-confidence regions are cleaner: "
          f"{high_confidence_error_lower}")
    summary["high_confidence_error_lower"] = high_confidence_error_lower
    summary["overall_test_error"] = round(overall_error, 4)
    summary["confident_region_error"] = None if confident_error is None else round(confident_error, 4)

    # ----------------------------------------------------------------
    # 6. selective prediction
    # ----------------------------------------------------------------
    sel_probs = test_variant[chosen]
    sel_labels = test_labels
    confidence = np.abs(sel_probs - 0.5)
    sel_order = np.argsort(-confidence)
    sel_rows = []
    for target in (1.0, 0.9, 0.8, 0.7):
        keep = max(1, int(round(target * len(sel_order))))
        idx = sel_order[:keep]
        kept_probs, kept_labels = sel_probs[idx], sel_labels[idx]
        preds = (kept_probs >= 0.5).astype(int)
        m = metrics_for(kept_probs, kept_labels)
        confident_keep = int(confident[idx].sum())
        sel_rows.append({
            "target_coverage": target,
            "achieved_coverage": round(keep / len(sel_order), 4),
            "n_answered": keep,
            "n_abstained": int(len(sel_order) - keep),
            "abstention_rule": "rank by |p - 0.5| (distance from the decision boundary)",
            **{k: m.get(k) for k in METRIC_KEYS},
            "roc_auc": round(float(roc_auc_score(kept_labels, kept_probs)), 4)
                if len(set(kept_labels.tolist())) > 1 else None,
            "n_inside_uncertainty_band": int(keep - confident_keep),
            "uncertainty_band_survivors": confident_keep,
            "coverage_vs_baseline_error": round(float(1 - m["accuracy"]), 4),
            "calibration_method": chosen,
            "source_bias_caveat": SOURCE_BIAS_CAVEAT,
        })
    write_csv("selective_prediction.csv", sel_rows)
    summary["selective_prediction"] = [{k: r[k] for k in
                                        ("target_coverage", "achieved_coverage",
                                         "accuracy", "balanced_accuracy", "fpr", "fnr",
                                         "roc_auc", "coverage_vs_baseline_error")} for r in sel_rows]

    # ----------------------------------------------------------------
    # 7. FP / FN transformation patterns
    # ----------------------------------------------------------------
    test_meta = [corpus[p] for p in test_paths]
    families = np.asarray([m["family"] for m in test_meta])
    sources = np.asarray([m["source"] for m in test_meta])
    generators = np.asarray([m["generator"] for m in test_meta])

    fp_rows, fn_rows = [], []
    flip_conditions = [c for c in CONDITIONS if c != "none"]
    for i, path in enumerate(test_paths):
        label = int(test_labels[i])
        p0 = float(base_probs[i])
        pred0 = int(base_pred[i])
        per_condition = {c: float(test_probs[c][i]) for c in flip_conditions}
        preds_c = {c: int(test_probs[c][i] >= 0.5) for c in flip_conditions}
        base_wrong = pred0 != label
        flipped = [c for c, p in preds_c.items() if p != pred0]
        newly_wrong = [c for c in flip_conditions if preds_c[c] != label]
        created = [c for c in newly_wrong if pred0 == label]
        if label == 0 and (base_wrong or created):
            fp_rows.append({
                "path": path, "source": sources[i], "family": families[i],
                "generator": generators[i], "true_label": "real",
                "baseline_probability": round(p0, 4), "baseline_prediction":
                    "synthetic (FP)" if base_wrong else "real (correct)",
                "conditions_where_flipped": "|".join(flipped),
                "conditions_newly_wrong": "|".join(created),
                "probabilities_by_condition": json.dumps({k: round(v, 4)
                                                           for k, v in per_condition.items()}),
                "max_probability_across_conditions": round(max(list(per_condition.values()) + [p0]), 4),
                "created_by_transform": "YES" if created else ("already wrong at baseline"
                                                               if base_wrong else "no"),
                "source_bias_caveat": SOURCE_BIAS_CAVEAT,
            })
        elif label == 1 and (base_wrong or created):
            fn_rows.append({
                "path": path, "source": sources[i], "family": families[i],
                "generator": generators[i], "true_label": "synthetic",
                "baseline_probability": round(p0, 4), "baseline_prediction":
                    "real (FN)" if base_wrong else "synthetic (correct)",
                "conditions_where_flipped": "|".join(flipped),
                "conditions_newly_wrong": "|".join(newly_wrong),
                "probabilities_by_condition": json.dumps({k: round(v, 4)
                                                           for k, v in per_condition.items()}),
                "min_probability_across_conditions": round(min(list(per_condition.values()) + [p0]), 4),
                "created_by_transform": "YES" if created else ("already wrong at baseline"
                                                               if base_wrong else "no"),
                "source_bias_caveat": SOURCE_BIAS_CAVEAT,
            })
    write_csv("robustness_false_positives.csv", fp_rows)
    write_csv("robustness_false_negatives.csv", fn_rows)

    fp_created = sum(1 for r in fp_rows if r["created_by_transform"] == "YES")
    fn_created = sum(1 for r in fn_rows if r["created_by_transform"] == "YES")
    summary["error_patterns"] = {
        "false_positives_total": len(fp_rows),
        "false_positives_created_by_transform": fp_created,
        "false_negatives_total": len(fn_rows),
        "false_negatives_created_by_transform": fn_created,
        "fp_created_by_condition": json.dumps(
            {c: sum(1 for r in fp_rows if c in r["conditions_newly_wrong"].split("|"))
             for c in flip_conditions}),
        "fn_created_by_condition": json.dumps(
            {c: sum(1 for r in fn_rows if c in r["conditions_newly_wrong"].split("|"))
             for c in flip_conditions}),
        "fp_created_by_source": json.dumps(
            {s: sum(1 for r in fp_rows if r["source"] == s and r["created_by_transform"] == "YES")
             for s in sorted(set(r["source"] for r in fp_rows))}),
    }
    print(f"\n=== error patterns ===\n  FP rows {len(fp_rows)} (created by transform: {fp_created})"
          f"\n  FN rows {len(fn_rows)} (created by transform: {fn_created})")

    # ----------------------------------------------------------------
    # 8. latency + model size
    # ----------------------------------------------------------------
    print("\n=== latency ===")
    single = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (128, 128, 128))
    tensor = FINAL_TRANSFORM(single).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        for _ in range(10):
            model(tensor)
        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
        n_iter = 100
        started = time.perf_counter()
        for _ in range(n_iter):
            model(tensor)
        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
        single_ms = (time.perf_counter() - started) / n_iter * 1000
    loader = DataLoader(ConditionDataset(test_paths[:256], test_labels[:256], "none"),
                        batch_size=BATCH_SIZE, num_workers=NUM_WORKERS)
    with torch.no_grad():
        model_started = time.perf_counter()
        for images, _ in loader:
            model(images.to(DEVICE))
        if DEVICE.type == "cuda":
            torch.cuda.synchronize()
        pipeline_ms = (time.perf_counter() - model_started) / 256 * 1000
    cpu_model = build_model()[0].to("cpu")
    with torch.no_grad():
        for _ in range(3):
            cpu_model(tensor.cpu())
        started = time.perf_counter()
        for _ in range(20):
            cpu_model(tensor.cpu())
        cpu_ms = (time.perf_counter() - started) / 20 * 1000
    latency = {
        "device": str(DEVICE),
        "gpu_single_image_ms": round(single_ms, 3),
        "gpu_batch32_throughput_ms_per_image": round(pipeline_ms, 3),
        "cpu_single_image_ms": round(cpu_ms, 3),
        "checkpoint_size_mb": round(model_size_mb, 3),
        "parameter_count": int(sum(p.numel() for p in model.parameters())),
        "trainable_parameter_count": int(sum(p.numel() for p in model.parameters() if p.requires_grad)),
        "input_size": f"{IMAGE_SIZE}x{IMAGE_SIZE}",
        "note": ("gpu_single_image_ms is pure forward pass at batch 1 (steady state, CUDA-synchronised). "
                 "gpu_batch32_throughput_ms_per_image includes disk read + decode + resize + normalise "
                 "with num_workers=4, so it is dominated by preprocessing, not by the network."),
    }
    write_csv("robustness_latency_and_size.csv", [latency])
    summary["latency"] = latency

    # ----------------------------------------------------------------
    # summary
    # ----------------------------------------------------------------
    summary["baseline_test_metrics"] = calib_detail["raw"]["metrics"]
    summary["checkpoint_stored_metrics"] = checkpoint.get("metrics")
    summary["conditions"] = {k: v["desc"] for k, v in CONDITIONS.items()}
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n  written: {SUMMARY.name}")

    print(f"\n{'=' * 72}\n=== HEADLINE (unperturbed test, {EXPERIMENT}) ===")
    base = calib_detail["raw"]["metrics"]
    print(f"  auc={base['roc_auc']} bal_acc={base['balanced_accuracy']} fpr={base['fpr']} "
          f"fnr={base['fnr']} brier={base['brier']}")
    print(f"\n{'=' * 72}\n=== JPEG ===")
    for r in group_tables["jpeg"]:
        print(f"  {r['condition']:10} auc={r['roc_auc']} bal_acc={r['balanced_accuracy']} "
              f"fpr={r['fpr']} fnr={r['fnr']} brier={r['brier']} shift={r['mean_probability_shift']}")
    print(f"=== RESOLUTION ===")
    for r in group_tables["resolution"]:
        print(f"  {r['condition']:10} auc={r['roc_auc']} bal_acc={r['balanced_accuracy']} "
              f"fpr={r['fpr']} fnr={r['fnr']} brier={r['brier']} shift={r['mean_probability_shift']}")
    print(f"=== WEB ===")
    for r in group_tables["web"]:
        print(f"  {r['condition']:16} auc={r['roc_auc']} bal_acc={r['balanced_accuracy']} "
              f"fpr={r['fpr']} fnr={r['fnr']}")
    print(f"\n{'=' * 72}\n=== CALIBRATION (fit on validation only) ===")
    for r in calib_rows:
        print(f"  {r['method']:12} test_brier={r['test_brier']} ece={r['test_ece']} "
              f"nll={r['test_nll']} auc={r['test_roc_auc']} spread={r['score_spread_std']} "
              f"worst_family={r['worst_family_balanced_accuracy']}")
    print(f"  selected: {chosen}")
    print(f"\n{'=' * 72}\n=== SELECTIVE PREDICTION ===")
    for r in sel_rows:
        print(f"  coverage {r['target_coverage']:.2f} -> acc={r['accuracy']} "
              f"bal_acc={r['balanced_accuracy']} fpr={r['fpr']} fnr={r['fnr']}")
    print(f"\n{'=' * 72}")
    print(f"  latency: gpu single {single_ms:.2f} ms/img, pipeline {pipeline_ms:.2f} ms/img, "
          f"cpu {cpu_ms:.2f} ms/img")
    print(f"  checkpoint size: {model_size_mb:.2f} MB")
    print(f"\n{SOURCE_BIAS_CAVEAT}")
    print(GENERALISATION_CAVEAT)
    print("  A robust result does NOT unblock promotion. Promotion remains gated on "
          "worst-family generalisation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())