"""
Production model loading and inference (Phase 2B).

Loads `models/basirah-url-v1.joblib`, enforces the feature-schema
contract before every load, and returns an honest availability status.

Two behaviours are load-bearing:

1. A schema mismatch REFUSES the model rather than feeding it
   misaligned input. A model fed permuted features still returns
   probabilities — confident, meaningless ones.

2. No trained model means `available = False`, never a fabricated
   probability. The risk engine then runs on heuristics alone and every
   response says so.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib

from app.core.config import MODELS_DIR
from app.ml.feature_schema import (
    FeatureSchemaMismatch,
    assert_schema_matches,
    model_feature_indices,
    model_feature_names,
)
from app.services.feature_extractor import extract_features, to_vector

logger = logging.getLogger(__name__)

# ====================================================================
# ACTIVE PRODUCTION MODEL
# ====================================================================
# The loader no longer hardcodes a filename. `models/ACTIVE_MODEL.json`
# names the bundle that serves production, so promoting or rolling back
# is an explicit, reviewable file edit rather than a code change that
# silently alters what every caller gets.
#
# Phase 2E promoted basirah-url-v3 over basirah-url-v1 on the evidence
# recorded in results/phase2e/promotion_decision.json. v1 is retained on
# disk and remains loadable by name.
ACTIVE_POINTER = MODELS_DIR / "ACTIVE_MODEL.json"

FALLBACK_BUNDLE = "basirah-url-v1.joblib"
DEFAULT_THRESHOLD = 0.993035

# Whether the active model is cleared for AUTOMATED ENFORCEMENT.
# Phishing detection with a URL-string-only model and no reputation or
# page-content signal has a materially non-trivial false-positive rate
# on ordinary legitimate URLs, so BASIRAH does not present its output as
# suitable for automatic blocking. Users may still act on a verdict,
# but the product says so rather than implying otherwise.
FIT_FOR_AUTOMATED_BLOCKING = False

SAFETY_NOTICE = (
    "This model is advisory only. It is not validated for automated "
    "blocking or takedown: on a curated set of 14 well-known legitimate "
    "URLs it misclassifies 5, and on held-out verified phishing it misses "
    "roughly a quarter at a 5% false-positive rate. Treat a verdict as "
    "evidence to review, not a decision to enforce."
)

# The operating threshold selected on the validation fold. Overridable
# per-request so experiments can compare thresholds without reloading.
DEFAULT_THRESHOLD = 0.993035


@dataclass(frozen=True)
class ProductionModel:
    """A loaded, schema-verified production model."""

    estimator: object
    feature_names: list[str]
    metadata: dict[str, object]
    threshold: float
    path: Path


@dataclass(frozen=True)
class InferenceResult:
    """Outcome of a production inference attempt."""

    available: bool
    probability: float | None
    model_name: str
    model_version: str
    threshold: float
    reason: str

    def as_percent(self) -> float | None:
        return None if self.probability is None else self.probability * 100.0

    def risk_percent(self) -> float | None:
        value = self.as_percent()
        return None if value is None else min(100.0, value)


def _pointer() -> dict[str, object]:
    """Which bundle serves production.

    Falls back to v1 if the pointer is missing or unreadable, so a
    damaged pointer degrades to the previous known-good model rather
    than to no model at all.
    """
    if ACTIVE_POINTER.exists():
        try:
            payload = json.loads(ACTIVE_POINTER.read_text(encoding="utf-8"))
            bundle = str(payload.get("bundle", "")).strip()
            if bundle:
                return {
                    "bundle": bundle,
                    "metadata": str(
                        payload.get("metadata", bundle.replace(".joblib", ".metadata.json"))
                    ),
                    "source": "pointer",
                }
        except Exception as exc:  # noqa: BLE001
            logger.error("ACTIVE_MODEL.json unreadable, falling back: %s", exc)
    return {
        "bundle": FALLBACK_BUNDLE,
        "metadata": FALLBACK_BUNDLE.replace(".joblib", ".metadata.json"),
        "source": "fallback",
    }


def model_path() -> Path:
    return MODELS_DIR / str(_pointer()["bundle"])


def metadata_path() -> Path:
    return MODELS_DIR / str(_pointer()["metadata"])


def safety_status() -> dict[str, object]:
    """What the API reports about fitness for enforcement."""
    return {
        "fit_for_automated_blocking": FIT_FOR_AUTOMATED_BLOCKING,
        "notice": SAFETY_NOTICE,
    }


@lru_cache(maxsize=1)
def load_production_model() -> ProductionModel | None:
    """Load and schema-verify the production model, or return None."""
    path = model_path()
    if not path.exists():
        logger.info("No production model at %s", path.name)
        return None

    try:
        bundle = joblib.load(path)
    except Exception as exc:  # noqa: BLE001
        # Any unpickling failure degrades to heuristics rather than 500ing.
        logger.error("Production model failed to load: %s", exc)
        return None

    if not isinstance(bundle, dict) or "estimator" not in bundle:
        logger.error("Production model bundle is malformed.")
        return None

    features = bundle.get("feature_names")
    if not isinstance(features, list) or not features:
        logger.error("Production model is missing its feature order.")
        return None

    metadata: dict[str, object] = {}
    if metadata_path().exists():
        try:
            metadata = json.loads(metadata_path().read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.error("Production metadata unreadable: %s", exc)

    # The contract gate. A model trained against a different extractor
    # version or a different feature order is refused outright.
    try:
        assert_schema_matches(
            list(features),
            metadata.get("feature_extractor_version"),
        )
    except FeatureSchemaMismatch as exc:
        logger.error("Production model schema mismatch: %s", exc)
        return None

    threshold = metadata.get("selected_threshold")
    return ProductionModel(
        estimator=bundle["estimator"],
        feature_names=list(features),
        metadata=metadata,
        threshold=float(threshold) if isinstance(threshold, (int, float)) else DEFAULT_THRESHOLD,
        path=path,
    )


def production_status() -> tuple[bool, str, dict[str, object]]:
    """Transparency payload for /api/model/info. No filesystem paths."""
    model = load_production_model()
    if model is None:
        return (
            False,
            "No trained model is available. Inference is running on the "
            "heuristic engine alone.",
            {},
        )

    meta = dict(model.metadata)
    return True, "Production model loaded.", meta


def predict_risk_production(normalized_url) -> InferenceResult:
    """Run the production model on a normalized URL."""
    model = load_production_model()

    if model is None:
        return InferenceResult(
            available=False,
            probability=None,
            model_name="none",
            model_version="0.0.0",
            threshold=DEFAULT_THRESHOLD,
            reason=(
                "No trained model available; the model component of the risk "
                "score is inactive and the heuristic engine is carrying the "
                "assessment on its own."
            ),
        )

    # Slice the full extractor output down to the columns the model
    # expects, using the SAME index list that training used. Both sides
    # derive it from MODEL_EXCLUDED_FEATURES, so they cannot disagree.
    indices = model_feature_indices()
    full_vector = to_vector(extract_features(normalized_url))
    vector = [full_vector[i] for i in indices]

    try:
        proba = model.estimator.predict_proba([vector])  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        logger.error("Production inference failed: %s", exc)
        return InferenceResult(
            available=False,
            probability=None,
            model_name=str(model.metadata.get("model_name", "unknown")),
            model_version=str(model.metadata.get("model_version", "unknown")),
            threshold=model.threshold,
            reason="Inference raised an error; the model component was skipped.",
        )

    classes = list(getattr(model.estimator, "classes_", [0, 1]))
    try:
        positive = classes.index(1)
    except ValueError:
        logger.error("Production model has no positive class.")
        return InferenceResult(
            available=False,
            probability=None,
            model_name=str(model.metadata.get("model_name", "unknown")),
            model_version=str(model.metadata.get("model_version", "unknown")),
            threshold=model.threshold,
            reason="Model has no positive class; inference was skipped.",
        )

    return InferenceResult(
        available=True,
        probability=float(proba[0][positive]),
        model_name=str(model.metadata.get("model_name", "basirah-url-v1")),
        model_version=str(model.metadata.get("model_version", "unknown")),
        threshold=model.threshold,
        reason="Production model inference completed.",
    )


def model_feature_count() -> int:
    return len(model_feature_names())
