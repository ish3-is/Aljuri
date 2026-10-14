"""
Model loading.

A trained model is an OPTIONAL artefact. If models/url_risk_model.joblib
is absent — which is the current, honest state, because no real dataset
has been acquired — the predictor reports `model_available = False` and
the risk engine falls back to heuristics alone.

It is deliberately NOT permitted for this module to fabricate a model,
substitute a randomly-initialised estimator, or return a hardcoded
"probability" that would look like intelligence but encode nothing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib

from app.core.config import MODELS_DIR, settings

logger = logging.getLogger(__name__)

ARTIFACT_BUNDLE_VERSION = 1


@dataclass(frozen=True)
class ModelBundle:
    """Everything needed to run inference reproducibly."""

    estimator: object
    """The fitted scikit-learn pipeline."""

    feature_names: list[str]
    """Feature order at training time. Inference must match exactly."""

    metadata: dict[str, object]
    """Model name, dataset provenance, evaluation metrics."""

    path: Path


@dataclass(frozen=True)
class ModelStatus:
    """Whether a usable model is present, and why not if it isn't."""

    available: bool
    reason: str
    path: Path
    metadata: dict[str, object] | None = None


def model_path() -> Path:
    return MODELS_DIR / settings.model_filename


def _metadata_path(bundle_path: Path) -> Path:
    return bundle_path.with_suffix(".metadata.json")


@lru_cache(maxsize=1)
def load_model() -> ModelBundle | None:
    """Load the trained model bundle, or None when unavailable.

    Cached, so a request does not re-read and unpickle the artefact on
    every call.
    """
    path = model_path()
    if not path.exists():
        logger.info("No trained model at %s; using heuristics only.", path.name)
        return None

    try:
        bundle = joblib.load(path)
    except Exception as exc:  # noqa: BLE001 - any unpickling failure must not 500
        # A corrupt or incompatible artefact must degrade to heuristics
        # rather than take the service down.
        logger.error("Failed to load model bundle at %s: %s", path, exc)
        return None

    if not isinstance(bundle, dict) or "estimator" not in bundle:
        logger.error("Model bundle at %s is malformed.", path)
        return None

    features = bundle.get("feature_names")
    if not isinstance(features, list) or not features:
        logger.error("Model bundle is missing its feature order.")
        return None

    meta_path = _metadata_path(path)
    metadata: dict[str, object] = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.error("Model metadata unreadable: %s", exc)

    return ModelBundle(
        estimator=bundle["estimator"],
        feature_names=list(features),
        metadata=metadata,
        path=path,
    )


def model_status() -> ModelStatus:
    """Transparency payload for GET /api/model/info.

    Deliberately exposes no filesystem paths beyond the model's filename,
    so the endpoint cannot be used to discover server layout.
    """
    bundle = load_model()
    if bundle is None:
        return ModelStatus(
            available=False,
            reason=(
                "No trained model is present. Inference is running on the "
                "heuristic engine alone. Train a model with "
                "scripts/train_url_model.py once a labelled dataset is "
                "available."
            ),
            path=model_path(),
        )

    meta = dict(bundle.metadata)
    meta["feature_count"] = len(bundle.feature_names)
    return ModelStatus(
        available=True,
        reason="Trained model loaded.",
        path=bundle.path,
        metadata=meta,
    )


def save_model(
    estimator: object,
    feature_names: list[str],
    metadata: dict[str, object],
) -> Path:
    """Persist the estimator, its feature order and its metadata."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = model_path()

    joblib.dump(
        {
            "bundle_version": ARTIFACT_BUNDLE_VERSION,
            "estimator": estimator,
            "feature_names": list(feature_names),
        },
        path,
    )

    meta_path = _metadata_path(path)
    meta_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Saved model bundle to %s", path.name)
    return path
