"""
Image model loading.

The image detector is RESEARCH-GRADE. Nothing in this module may imply
otherwise, and the flags below are the single source of that status.

Which checkpoint
----------------
`models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt`

That model trained on GAN + PixelDiffusion + LatDiff and was evaluated
against Midjourney, an entirely unseen generator family: ROC-AUC 0.9832,
balanced accuracy 0.9311.

The older single-family checkpoint scoring 0.9984 is deliberately NOT
used. That number was within-family: the same model scored 0.3954
(below chance) on external transfer and accused 89.7% of genuine
photographs. Presenting 0.9984 as a capability would misrepresent the
detector by roughly 0.6 AUC.

Loading is pointer-based via RESEARCH_IMAGE_MODEL.json so the served
checkpoint is an explicit, reviewable file rather than a hardcoded name.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torchvision import models

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
POINTER = MODELS_DIR / "RESEARCH_IMAGE_MODEL.json"

FALLBACK_CHECKPOINT = Path(
    "multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt"
)

MODEL_STATUS = "research_grade"
ADVISORY_ONLY = True
FIT_FOR_AUTOMATED_ENFORCEMENT = False

MODEL_VERSION = "0.9.0-research"

SAFETY_NOTICE_EN = (
    "BASIRAH Image is a research-grade detector. It performs well within "
    "the generator families it was trained on, but its accuracy drops "
    "sharply on families it has never seen, and on very low-resolution "
    "images. Results are advisory and must not be used for automated "
    "blocking or as proof that an image is synthetic."
)
SAFETY_NOTICE_AR = (
    "نموذج صور BASIRAH نموذج بحثي. أداؤه جيد ضمن عائلات المولّدات التي "
    "دُرِّب عليها، لكنه يتراجع بحدة على عائلات لم يرها من قبل، وعلى "
    "الصور منخفضة الدقة جدًا. النتائج إرشادية ولا يجوز استخدامها "
    "للحظر الآلي أو كدليل قاطع على أن الصورة اصطناعية."
)

#: Warning threshold from the measured resolution-robustness sweep:
#: at 128px effective resolution balanced accuracy fell to 0.6919 and
#: 62% of genuine photographs were called synthetic.
LOW_RESOLUTION_LONG_EDGE = 192


def _pointer() -> dict[str, Any]:
    if POINTER.exists():
        try:
            return json.loads(POINTER.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.error("RESEARCH_IMAGE_MODEL.json unreadable: %s", exc)
    return {
        "checkpoint": str(FALLBACK_CHECKPOINT),
        "status": MODEL_STATUS,
        "advisory_only": ADVISORY_ONLY,
        "fit_for_automated_enforcement": FIT_FOR_AUTOMATED_ENFORCEMENT,
    }


class ImageModel:
    def __init__(self, checkpoint: Path, architecture: str, meta: dict[str, Any]):
        self.checkpoint = checkpoint
        self.architecture = architecture
        self.meta = meta
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
        payload = torch.load(checkpoint, map_location=self.device, weights_only=False)
        model.load_state_dict(payload["state_dict"])
        self.estimator = model.to(self.device).eval()
        self.model_version = str(payload.get("model_version", MODEL_VERSION))

    def predict(self, tensor: np.ndarray) -> float:
        """P(synthetic) for one preprocessed CHW float tensor."""
        with torch.no_grad():
            batch = torch.from_numpy(tensor).unsqueeze(0).to(self.device)
            return float(torch.softmax(self.estimator(batch), dim=1)[0, 1].item())


@lru_cache(maxsize=1)
def load_image_model() -> tuple[ImageModel | None, str]:
    """Returns (model, reason). `model` is None when unavailable.

    An unavailable model is reported honestly rather than replaced with a
    fabricated default probability.
    """
    pointer = _pointer()
    relative = pointer.get("checkpoint") or str(FALLBACK_CHECKPOINT)
    checkpoint = MODELS_DIR / relative
    if not checkpoint.exists():
        return None, f"research image checkpoint not found: {relative}"
    try:
        return (
            ImageModel(checkpoint, "efficientnet_b0", pointer),
            "",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("image model load failed: %s", exc)
        return None, f"research image model could not be loaded: {type(exc).__name__}"


def model_status() -> dict[str, Any]:
    model, reason = load_image_model()
    pointer = _pointer()
    return {
        "modelName": "BASIRAH Image Research Candidate",
        "modelVersion": model.model_version if model else MODEL_VERSION,
        "architecture": "EfficientNet-B0 (transfer learning, multi-family)",
        "available": model is not None,
        "reason": reason or None,
        "status": MODEL_STATUS,
        "advisoryOnly": ADVISORY_ONLY,
        "fitForAutomatedEnforcement": FIT_FOR_AUTOMATED_ENFORCEMENT,
        "noticeEn": SAFETY_NOTICE_EN,
        "noticeAr": SAFETY_NOTICE_AR,
        "checkpoint": pointer.get("checkpoint"),
        "why_not_single_family_model": (
            "The 0.9984 within-family checkpoint is not served. The same "
            "model scored 0.3954 on external cross-family transfer and "
            "misclassified 89.7% of genuine photographs as synthetic."
        ),
        "knownLimitations": [
            "Worst held-out generator family (GAN): balanced accuracy 0.5512, near chance.",
            "Source classifier reaches 0.9709 AUC, so the representation "
            "partly encodes which corpus an image came from.",
            "At 128px effective resolution balanced accuracy falls to 0.6919 "
            "and 62% of genuine photographs are called synthetic.",
        ],
        "trainedFamilies": ["GAN", "PixelDiffusion", "LatDiff"],
        "evaluatedHeldOutFamily": "Midjourney (architecture undisclosed)",
    }
