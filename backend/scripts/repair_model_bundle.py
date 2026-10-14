"""Repair the saved production bundle's stored feature list.

The bundle was trained on the 39-column model-input slice but stored the
full 41-name extractor list. The loader's schema guard correctly refused
it. This rewrites the stored feature_names to the model-input list the
estimator was actually fitted on, and updates the metadata to match.

The estimator itself is untouched — only the description of its inputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.feature_schema import (
    FEATURE_EXTRACTOR_VERSION,
    MODEL_EXCLUDED_FEATURES,
    assert_schema_matches,
    current_schema,
    model_feature_names,
)

MODELS = Path(__file__).resolve().parents[1] / "models"
BUNDLE = MODELS / "basirah-url-v1.joblib"
METADATA = MODELS / "basirah-url-v1.metadata.json"


def main() -> int:
    if not BUNDLE.exists():
        print("No bundle to repair.")
        return 1

    bundle = joblib.load(BUNDLE)
    estimator = bundle["estimator"]
    stored = list(bundle.get("feature_names", []))

    model_names = model_feature_names()
    print(f"stored feature count : {len(stored)}")
    print(f"model input count    : {len(model_names)}")

    if stored == model_names:
        print("Already correct; nothing to do.")
        return 0

    # Prove the estimator really was fitted on this width before relabelling.
    n_features = getattr(estimator, "n_features_in_", None)
    print(f"estimator n_features_in_ : {n_features}")
    if n_features is not None and int(n_features) != len(model_names):
        print(
            f"REFUSING: the estimator expects {n_features} features but the "
            f"model input list has {len(model_names)}. The bundle does not "
            f"match the training slice and cannot be relabelled safely."
        )
        return 2

    bundle["feature_names"] = model_names
    joblib.dump(bundle, BUNDLE)
    print("bundle feature_names rewritten to the model-input slice")

    if METADATA.exists():
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
        schema = current_schema()
        metadata["features"] = model_names
        metadata["feature_count"] = len(model_names)
        metadata["features_computed_by_extractor"] = schema.feature_names
        metadata["excluded_features"] = sorted(MODEL_EXCLUDED_FEATURES)
        metadata["excluded_feature_rationale"] = (
            "uses_https/uses_http have an inverted class association "
            "between PhiUSIIL and MUD-2026 (lift +2.06 vs -0.89); they are "
            "computed and displayed but are not model inputs."
        )
        METADATA.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print("metadata updated")

    # Final gate: the loader's own assertion must now pass.
    assert_schema_matches(model_names, FEATURE_EXTRACTOR_VERSION)
    print("schema assertion passes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
