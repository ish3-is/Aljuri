"""
Model inference.

Wraps the trained classifier behind an interface that is honest about
availability. `predict_risk` always returns a Prediction carrying an
`available` flag; the risk engine uses the probability only when the
model is genuinely loaded and the feature order matches.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.ml.model_loader import load_model
from app.services.feature_extractor import extract_features, to_vector

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Prediction:
    """Outcome of a model inference attempt."""

    available: bool
    """False when no trained model is loaded. Never faked."""

    probability: float | None
    """P(phishing) in 0-1, or None when unavailable."""

    model_name: str
    model_version: str
    reason: str

    def as_percent(self) -> float | None:
        return None if self.probability is None else self.probability * 100.0

    def risk_percent(self) -> float | None:
        """Model risk on the 0-100 scale used by the fusion formula."""
        value = self.as_percent()
        return None if value is None else min(100.0, value)


def predict_risk(url) -> Prediction:
    """Run inference for a normalized URL.

    Returns an unavailable Prediction — not a guess — when no model is
    loaded or the feature contract has drifted.
    """
    bundle = load_model()

    if bundle is None:
        return Prediction(
            available=False,
            probability=None,
            model_name="none",
            model_version="0.0.0",
            reason=(
                "No trained model available; the model component of the "
                "risk score is inactive and the heuristic engine is "
                "carrying the assessment on its own."
            ),
        )

    features = extract_features(url)
    vector = to_vector(features)

    # Guard against train/serve feature drift. If the extractor gains or
    # loses a feature after training, a silent misalignment would
    # produce confident nonsense.
    if vector.__len__() != len(bundle.feature_names):
        logger.error(
            "Feature count mismatch: model expects %d, extractor produced %d.",
            len(bundle.feature_names),
            len(vector),
        )
        return Prediction(
            available=False,
            probability=None,
            model_name=str(bundle.metadata.get("model_name", "unknown")),
            model_version=str(bundle.metadata.get("model_version", "unknown")),
            reason=(
                "Feature contract mismatch between the trained model and "
                "the current extractor; model inference was skipped."
            ),
        )

    try:
        proba = bundle.estimator.predict_proba([vector])  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        logger.error("Inference failed: %s", exc)
        return Prediction(
            available=False,
            probability=None,
            model_name=str(bundle.metadata.get("model_name", "unknown")),
            model_version=str(bundle.metadata.get("model_version", "unknown")),
            reason="Inference raised an error; the model component was skipped.",
        )

    # Column order follows the classes seen at fit time. Locate the
    # positive class rather than assuming index 1, so a label-mapping
    # surprise cannot silently invert the score.
    classes = list(getattr(bundle.estimator, "classes_", [0, 1]))
    try:
        positive_index = classes.index(1)
    except ValueError:
        logger.error("Model classes %s contain no positive label.", classes)
        return Prediction(
            available=False,
            probability=None,
            model_name=str(bundle.metadata.get("model_name", "unknown")),
            model_version=str(bundle.metadata.get("model_version", "unknown")),
            reason="Model has no positive class; inference was skipped.",
        )

    probability = float(proba[0][positive_index])

    return Prediction(
        available=True,
        probability=probability,
        model_name=str(bundle.metadata.get("model_name", "unknown")),
        model_version=str(bundle.metadata.get("model_version", "unknown")),
        reason="Model inference completed.",
    )
