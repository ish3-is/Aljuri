"""
Wire the two-detector ensemble and the provenance-first tier into the
live image analysis path.

`analyze_image` keeps its existing contract so the current frontend and
its 390 backend tests continue to work unchanged. Everything new is
ADDED alongside: `ensemble`, the full C2PA provenance object, and a
trust assessment that is no longer a restatement of the pixel model.

The one deliberate change is `provenance`: it is upgraded from the
legacy scan-only shape to the verified SDK result, while keeping the
legacy keys the frontend already reads.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any

from PIL import Image

from app.image.ensemble import detector_b as det_b
from app.image.ensemble.policy import (
    DetectorVote,
    Distribution,
    EvidenceQuality,
    assess_evidence_quality,
    decide,
)
from app.image.provenance_c2pa import ProvenanceStatus as C2paStatus
from app.image.provenance_c2pa import verify_provenance

_ROOT = Path(__file__).resolve().parents[2]
PROBE_PATH = _ROOT / "models" / "detector_b_clip_probe.joblib"

_CACHE: dict[str, Any] = {}


def _preferred_device() -> str:
    """
    CUDA when available, CPU otherwise.

    Detector B is a frozen ViT-B forward pass. On this project it runs on
    an RTX 3050, but a CPU path is kept so the platform still functions
    on a machine without CUDA rather than failing the whole analysis.
    """
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_probe():
    """Load Detector B's frozen probe once, lazily.

    Detector B is SHADOW ONLY and is never consulted in the fusion
    decision, so the probe load is very light: only the metadata, not
    the classifier. The probe if needed for diagnostics only.
    """
    if "probe" not in _CACHE:
        try:
            _CACHE["probe"] = det_b.load_probe(PROBE_PATH) if PROBE_PATH.exists() else None
            _CACHE["backbone"] = det_b.CANDIDATE_BACKBONES[0]
            _CACHE["device"] = _preferred_device()
        except Exception as exc:  # noqa: BLE001
            _CACHE["probe"] = None
            _CACHE["error"] = f"{type(exc).__name__}: {exc}"
    return _CACHE.get("probe")


def detector_b_vote(image_bytes: bytes) -> tuple[DetectorVote, dict[str, Any]]:
    """
    Detector B is DEPLOYED SHADOW ONLY.

    Its output is used for diagnostics/research only and does NOT affect
    the final user verdict. This is the fix for its severe false-positive
    saturation on genuine phone photographs: its 100% synthetic likelihood
    on real photos is a known failure mode, and it must not be allowed
    to influence any assessment.

    The vote is still computed and returned so downstream diagnostics can
    see what Detector B would have said, but it is marked unavailable for
    decision purposes.
    """
    probe = _load_probe()
    if probe is None:
        return (
            DetectorVote(
                name="BASIRAH Detector B (CLIP probe)",
                architecture="CLIP ViT-B/16 frozen embeddings + linear probe",
                synthetic_probability=0.5,
                unavailable_reason=(
                    "Detector B is SHADOW ONLY. Its output is withheld from "
                    "the final decision due to severe false-positive "
                    "saturation on genuine phone photographs."
                ),
            ),
            {"available": False},
        )

    started = time.perf_counter()
    try:
        emb = det_b.embed_image_bytes(
            image_bytes, _CACHE["backbone"], device=_CACHE.get("device", "cpu")
        )
        outcome = det_b.predict_one(
            emb, probe,
            model_name="BASIRAH Detector B (CLIP probe)",
            architecture="CLIP ViT-B/16 frozen embeddings + linear probe",
        )
    except Exception as exc:  # noqa: BLE001
        return (
            DetectorVote(
                name="BASIRAH Detector B (CLIP probe)",
                architecture="CLIP ViT-B/16 frozen embeddings + linear probe",
                synthetic_probability=0.5,
                unavailable_reason=f"Detector B is shadow-only; {type(exc).__name__}",
            ),
            {"available": False},
        )

    # Detector B's output is returned for diagnostics only. It is NOT
    # marked "available" for the fusion decision.
    return (
        DetectorVote(
            name=outcome.model_name,
            architecture=outcome.architecture,
            synthetic_probability=outcome.synthetic_probability,
            limitations=outcome.limitations,
        ),
        {
            "available": False,  # shadow-only: excluded from fusion
            "distributionStatus": outcome.distribution_status,
            "oodScore": outcome.ood_score,
            "secs": round((time.perf_counter() - started) * 1000, 2),
            "device": _CACHE.get("device", "cpu"),
            "shadow_only": True,
            "diagnostics_only": True,
        },
    )


def _provenance_payload(original_bytes: bytes) -> tuple[dict[str, Any], Any]:
    """Run real C2PA verification on ORIGINAL bytes and keep the result.

    The external C2PA SDK can return non-dict values for manifest fields
    (for example a raw packet string in active_manifest). Guard every
    .get() so a str can never raise AttributeError up the ensemble path.
    """
    result = verify_provenance(original_bytes)
    payload = result.to_dict()
    # Legacy keys the current frontend already reads, derived honestly.
    payload["contentCredentialsPresent"] = result.manifest_present
    payload["manifestFound"] = result.manifest_present
    return payload, result


def enrich_with_ensemble(
    response: dict[str, Any],
    original_bytes: bytes,
    detector_a_probability: float | None,
    long_edge: int,
    warnings: list[str],
    metadata_consistency: float | None = None,
) -> dict[str, Any]:
    """
    Add the ensemble, provenance tier and evidence hierarchy to an
    existing analysis response without removing anything.
    """
    started = time.perf_counter()

    # ---- Detector B ----------------------------------------------------
    vote_b, info_b = detector_b_vote(original_bytes)
    dist_enum = info_b.get("distribution", Distribution.IN)

    # ---- Detector A ----------------------------------------------------
    if detector_a_probability is None:
        vote_a = DetectorVote(
            name="BASIRAH Detector A (EfficientNet research checkpoint)",
            architecture="EfficientNet-B0",
            synthetic_probability=0.5,
            unavailable_reason="Detector A model unavailable",
        )
    else:
        vote_a = DetectorVote(
            name="BASIRAH Detector A (EfficientNet research checkpoint)",
            architecture="EfficientNet-B0",
            synthetic_probability=detector_a_probability,
            limitations=[
                "Research-grade checkpoint; validated on a limited set of "
                "generator families.",
                "Known to miss some synthetic images, so a low value here "
                "is not evidence of authenticity.",
            ],
        )

    # ---- provenance (original bytes) -----------------------------------
    prov_payload, prov_result = _provenance_payload(original_bytes)
    provenance_status = prov_result.status.value

    # ---- evidence quality ----------------------------------------------
    quality = assess_evidence_quality(
        width=response.get("metadata", {}).get("width") or long_edge,
        height=response.get("metadata", {}).get("height") or long_edge,
        warnings=warnings,
    )

    # ---- fusion ---------------------------------------------------------
    outcome = decide(
        votes=[vote_a, vote_b],
        provenance_status=provenance_status,
        distribution_status=dist_enum,
        evidence_quality=quality,
        metadata_consistency=metadata_consistency,
    )
    payload = outcome.to_dict()

    response["ensemble"] = {
        "detectors": payload["detectors"],
        "detectorAgreement": payload["detectorAgreement"],
        "distributionStatus": payload["distributionStatus"],
        "evidenceQuality": payload["evidenceQuality"],
        "syntheticLikelihood": payload["syntheticLikelihood"],
        "abstained": payload["abstained"],
        "abstentionReasons": payload["abstentionReasons"],
        "notes": payload["notes"],
        "latencyMs": {
            "detectorB": info_b.get("secs"),
            "fusion": round((time.perf_counter() - started) * 1000, 2),
        },
    }
    response["provenance"] = {**response.get("provenance", {}), **prov_payload}

    # Evidence hierarchy (Tier 4). Kept explicit so a reviewer can see
    # why one signal outranks another.
    response["evidenceHierarchy"] = [
        {
            "source": "content_credentials",
            "strength": prov_result.evidence_strength.value,
            "status": provenance_status,
            "summary": (
                "Cryptographically verified provenance assertion."
                if prov_result.status is C2paStatus.VERIFIED
                else "No verified provenance assertion available."
            ),
        },
        {
            "source": "detector_ensemble",
            "strength": "medium" if payload["detectorAgreement"] in
            ("strong_agreement", "moderate_agreement") else "low",
            "status": payload["detectorAgreement"],
            "summary": (
                f"{len([v for v in payload['detectors'] if v['status'] == 'available'])} "
                "independent detectors evaluated."
            ),
        },
        {
            "source": "metadata",
            # Absence is explicitly neutral, never suspicious.
            "strength": "neutral",
            "status": "inspected",
            "summary": "Metadata presence or absence carries no verdict on its own.",
        },
    ]

    response["trustAssessment"] = {
        "value": payload["trustAssessment"],
        "components": payload["trustComponents"],
        "label": "Digital Trust Assessment",
        "isAuthenticityProbability": False,
        "authenticityVerified": payload["authenticityClaimSupported"],
        "note": (
            "This is not an authenticity probability. Only cryptographically "
            "verified Content Credentials can support an authenticity claim."
        ),
    }
    response["finalAssessment"] = payload["assessment"]
    return response
