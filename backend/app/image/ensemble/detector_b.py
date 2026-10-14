"""
Detector B — an independent second opinion for BASIRAH image advisory.

Motivation
----------
The single EfficientNet-B0 research checkpoint cannot, by itself, ever
support a claim that an image is authentic. Agreement between two
detectors is only meaningful if the second detector is genuinely
independent, so this module deliberately differs from Detector A in
every dimension that matters:

    Detector A : EfficientNet-B0 CNN, ImageNet-supervised transfer
                 learning, trained on the BASIRAH corpus.
    Detector B : CLIP image encoder (ViT/ConvNeXt), pre-trained on
                 LAION-2B image-text pairs, with a LINEAR probe fitted
                 on frozen embeddings.

Different architecture, different pre-training corpus, different
inductive bias. Nothing is trained from scratch: the backbone is frozen
and only a logistic-regression head is fitted, which is the standard
"frozen embedding classifier" the brief permits.

OOD handling
------------
The same frozen embedding space gives a cheap, defensible
unfamiliarity signal. A kNN distance to the training embeddings is
computed at fit time and stored, so a novel input can be flagged
without any retraining. This matters more than raw accuracy: it is what
lets BASIRAB abstain instead of guessing.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np

# Frozen-embedding CLIP encoders available locally through timm.
# LAION-2B is web-scale image-text supervision, which is a genuinely
# different data distribution from ImageNet classification labels, so
# the two detectors do not share the same shortcuts.
# DEPLOYMENT POLICY (recalibration pass): Detector B is SHADOW ONLY.
# It does not participate in the fusion decision. Its output is used
# for diagnostics/research only.
CANDIDATE_BACKBONES = (
    "vit_base_patch16_clip_224.openai",
    "convnext_base.clip_laion2b",
    "convnext_tiny.clip_laion2b",
)

# Embeddings are L2-normalised before the probe, so distances live in a
# comparable range regardless of backbone width.
EMBED_DIM_HINT = {"vit_base_patch16_clip_224.openai": 768}

# Process-wide backbone cache: {(name, device): (model, transform)}.
# Populated on first use so importing this module stays cheap.
_BACKBONE_CACHE: dict[tuple[str, str], Any] = {}


@dataclass
class DetectorBResult:
    """Single-detector output. Never claims authenticity on its own."""

    model_name: str
    architecture: str
    synthetic_probability: float
    confidence: float
    status: str
    distribution_status: str = "in_distribution"
    ood_score: float | None = None
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelName": self.model_name,
            "architecture": self.architecture,
            "syntheticProbability": round(float(self.synthetic_probability), 6),
            "confidence": round(float(self.confidence), 6),
            "status": self.status,
            "distributionStatus": self.distribution_status,
            "oodScore": None if self.ood_score is None else round(float(self.ood_score), 6),
            "limitations": list(self.limitations),
        }


def build_backbone(name: str):
    """Load a frozen timm feature extractor. Deliberately fails loudly."""
    import torch
    import timm

    model = timm.create_model(name, pretrained=True, num_classes=0)
    model.eval()
    for param in model.parameters():  # frozen probe: no gradient ever flows
        param.requires_grad_(False)
    cfg = timm.data.resolve_data_config({}, model=model)
    return model, cfg


def transform_for(cfg: dict[str, Any]):
    import timm
    return timm.data.create_transform(**cfg, is_training=False)



def embed_images(
    paths: Sequence[str],
    backbone: str,
    batch_size: int = 32,
    device: str = "cpu",
    progress_every: int = 0,
):
    """Return L2-normalised CLIP embeddings for the given image paths."""
    import torch
    from PIL import Image

    model, cfg = build_backbone(backbone)
    transform = transform_for(cfg)
    model = model.to(device)

    feats: list[np.ndarray] = []
    pending: list[Any] = []

    with torch.no_grad():
        for idx, p in enumerate(paths):
            with Image.open(p) as im:
                pending.append(transform(im.convert("RGB")))
            if len(pending) == batch_size or idx == len(paths) - 1:
                tensor = torch.stack(pending).to(device)
                pending = []
                out = model(tensor)
                if isinstance(out, (list, tuple)):
                    out = out[0]
                feats.append(out.float().cpu().numpy())
            if progress_every and idx % progress_every == 0:
                print(f"    embedded {idx + 1}/{len(paths)}", flush=True)

    matrix = np.concatenate(feats, axis=0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _get_backbone(name: str, device: str):
    """
    Load and cache the frozen backbone.

    The CLIP checkpoint is ~350 MB. Re-loading it per request would add
    seconds to every analysis, so it is held once and reused. The cache
    is keyed by (name, device) because a tensor cannot move between
    devices after creation.
    """
    key = (name, device)
    if key not in _BACKBONE_CACHE:
        model, cfg = build_backbone(name)
        model = model.to(device)
        transform = transform_for(cfg)
        _BACKBONE_CACHE[key] = (model, transform)
    return _BACKBONE_CACHE[key]


def embed_image_bytes(data: bytes, backbone: str, device: str = "cpu"):
    """
    Embed a single in-memory image.

    The API receives bytes, so writing a temporary file only to read it
    back would add I/O and a cleanup failure mode for no benefit. The
    transform pipeline is identical to `embed_images`, so detections
    are consistent with the batch path.
    """
    import torch
    from PIL import Image

    model, transform = _get_backbone(backbone, device)

    with Image.open(io.BytesIO(data)) as opened:
        tensor = transform(opened.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(tensor)
    if isinstance(out, (list, tuple)):
        out = out[0]
    vector = out.float().cpu().numpy()[0]
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError("embedder produced a zero vector")
    return vector / norm


def fit_probe(embeddings: np.ndarray, labels: np.ndarray, seed: int = 20261005):
    """Fit the linear head and the kNN OOD reference in one pass."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(embeddings)
    clf = LogisticRegression(max_iter=2000, C=1.0, random_state=seed)
    clf.fit(scaler.transform(embeddings), labels)

    # Cosine similarity of every training point to its nearest neighbour.
    # A novel image lands far from every stored embedding, which is the
    # signal used later to abstain.
    sims = embeddings @ embeddings.T
    np.fill_diagonal(sims, -np.inf)
    nn_sim = sims.max(axis=1)

    return {
        "scaler": scaler,
        "classifier": clf,
        "embeddings": embeddings.astype(np.float32),
        "labels": labels.astype(np.int8),
        "nn_sim_mean": float(nn_sim.mean()),
        "nn_sim_std": float(nn_sim.std()),
        "nn_sim_p05": float(np.percentile(nn_sim, 5)),
        "n_train": int(len(labels)),
        "positive_rate": float(labels.mean()),
    }


def knn_distance_score(embedding: np.ndarray, store: dict[str, Any]) -> float:
    """1 - (max cosine similarity to any stored training embedding)."""
    ref = store["embeddings"]
    sims = ref @ embedding
    return float(1.0 - sims.max())


def distribution_status(score: float, store: dict[str, Any]) -> str:
    """
    Three-way unfamiliarity verdict from the kNN distance.

    The "borderline" boundary is the 5th percentile of the training
    set's own nearest-neighbour similarity, so it is derived from the
    data rather than picked by hand.
    """
    mean, std = store["nn_sim_mean"], store["nn_sim_std"]
    p05 = store["nn_sim_p05"]
    sim = 1.0 - score
    if sim >= mean - 2 * std:
        return "in_distribution"
    if sim >= p05:
        return "borderline"
    return "out_of_distribution"


def predict_one(embedding: np.ndarray, store: dict[str, Any], model_name: str,
                architecture: str) -> DetectorBResult:
    prob = float(store["classifier"].predict_proba(
        store["scaler"].transform(embedding.reshape(1, -1))
    )[0, 1])
    score = knn_distance_score(embedding, store)
    dist = distribution_status(score, store)
    # Confidence is kept separate from the synthetic probability on
    # purpose: a probability near 0.5 is a weak claim even when the
    # embedding looks familiar.
    confidence = float(abs(prob - 0.5) * 2.0)
    return DetectorBResult(
        model_name=model_name,
        architecture=architecture,
        synthetic_probability=prob,
        confidence=confidence,
        status="available",
        distribution_status=dist,
        ood_score=score,
        limitations=[
            "Frozen CLIP embedding with a linear probe; no end-to-end training.",
            "Validated only on the BASIRAH corpus families.",
            "Cannot support an authenticity claim; it estimates synthetic likelihood.",
        ],
    )


def save_probe(store: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(store, path)


def load_probe(path: Path) -> dict[str, Any]:
    return joblib.load(path)


def probe_metadata(path: Path) -> dict[str, Any]:
    store = load_probe(path)
    return {
        "checkpoint": path.name,
        "n_train": store["n_train"],
        "embedding_dim": int(store["embeddings"].shape[1]),
        "positive_rate": store["positive_rate"],
        "nn_sim_mean": store["nn_sim_mean"],
        "nn_sim_std": store["nn_sim_std"],
        "nn_sim_p05": store["nn_sim_p05"],
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps({"backbones": list(CANDIDATE_BACKBONES)}, indent=2))
