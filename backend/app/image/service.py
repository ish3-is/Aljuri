"""
Image analysis service.

Orchestrates the pipeline the Phase 3 brief specifies:

    received -> validated -> decoded -> metadata -> provenance
             -> forensics -> model inference -> evidence correlation
             -> uncertainty -> trust assessment

Design commitments carried from the research phases:

* **Model probability and evidence quality are separate concepts.** A
  low-resolution image does not get its probability adjusted; it gets a
  warning, because inventing a number the model cannot support is worse
  than reporting the number it produced plus a caveat.
* **Uncertainty is a first-class outcome.** The uncertain band uses the
  thresholds measured on validation data during Phase 3, not 0.5.
* **Weak channels cannot manufacture confidence.** Metadata and forensics
  are corroborating context only.
* **No mock fallback.** If the model is unavailable the service says so.
"""

from __future__ import annotations

import time
from typing import Any

from app.image.forensics import analyze as analyze_forensics
from app.image.metadata import extract_metadata
from app.image.model_loader import (
    LOW_RESOLUTION_LONG_EDGE,
    load_image_model,
    model_status,
)
from app.image.preprocessing import CONTRACT, preprocess_bytes
from app.image.provenance import ProvenanceStatus, inspect_provenance
from app.image.risk_engine import assess
from app.image.ensemble_integration import enrich_with_ensemble
from app.image.schemas import Assessment
from app.image.validation import ImageValidationError, validate_upload

#: Measured on validation data in Phase 3 (uncertify_policy.csv).
UNCERTAINTY_LOWER = 0.50
UNCERTAINTY_UPPER = 0.807


class ImageAnalysisError(Exception):
    def __init__(self, message: str, code: str = "image_analysis_failed") -> None:
        super().__init__(message)
        self.code = code


def _timeline(stage: str, evidence: str, status: str = "complete") -> dict[str, Any]:
    return {"stage": stage, "evidence": evidence, "status": status}


def analyze_image(
    data: bytes,
    *,
    original_name: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Analyse an uploaded image. Raises ImageValidationError on bad input."""
    started = time.perf_counter()
    events: list[dict[str, Any]] = []

    # ---- validate ----------------------------------------------------
    try:
        validated = validate_upload(
            data, original_name=original_name, declared_content_type=content_type
        )
    except ImageValidationError:
        raise
    events.append(_timeline("image_validated", f"{validated.fmt}, {len(data)} bytes"))
    events.append(_timeline("image_decoded", f"{validated.width}x{validated.height}"))

    # ---- metadata ----------------------------------------------------
    metadata = extract_metadata(validated)
    events.append(_timeline(
        "metadata_inspected",
        "EXIF present" if metadata.exif_present else "no EXIF",
    ))

    # ---- provenance --------------------------------------------------
    provenance = inspect_provenance(validated.data)
    events.append(_timeline("provenance_checked", provenance.status.value))

    # ---- forensics ---------------------------------------------------
    forensics = analyze_forensics(validated)
    events.append(_timeline(
        "forensic_signals_computed",
        f"{len([s for s in forensics.signals if s.value is not None])} measurable signals",
    ))

    # ---- model -------------------------------------------------------
    model, reason = load_image_model()
    probability: float | None = None
    if model is None:
        events.append(_timeline("synthetic_model_unavailable", reason, status="warning"))
    else:
        prepared = preprocess_bytes(data)
        probability = model.predict(prepared.tensor)
        events.append(_timeline(
            "synthetic_media_inference",
            f"P(synthetic)={probability:.4f}",
        ))

    # ---- evidence correlation + risk ---------------------------------
    risk = assess(
        synthetic_probability=probability,
        metadata=metadata,
        forensics=forensics,
        provenance=provenance,
    )

    # Measured Phase 3 thresholds, not an arbitrary 0.5.
    if probability is None:
        assessment = Assessment.UNCERTAIN
        uncertain = True
    elif probability >= UNCERTAINTY_UPPER:
        assessment, uncertain = Assessment.LIKELY_SYNTHETIC, False
    elif probability <= UNCERTAINTY_LOWER:
        assessment, uncertain = Assessment.LIKELY_AUTHENTIC, False
    else:
        assessment, uncertain = Assessment.UNCERTAIN, True

    # ---- evidence quality (kept separate from the probability) --------
    long_edge = max(validated.width, validated.height)
    quality_warnings: list[dict[str, str]] = []
    if long_edge <= LOW_RESOLUTION_LONG_EDGE:
        quality_warnings.append({
            "code": "low_resolution",
            "severity": "high",
            "en": ("Image resolution is too low for reliable synthetic-media "
                   "analysis. In testing, images at this size lost most of "
                   "their accuracy and genuine photographs were frequently "
                   "misclassified."),
            "ar": ("دقة الصورة منخفضة جدًا وقد تقلل موثوقية التحليل. في "
                   "الاختبارات، فقدت الصور بهذا الحجم معظم دقتها وصُنِّفت "
                   "صور فوتوغرافية أصلية خطأً في حالات كثيرة."),
        })
    if validated.fmt == "JPEG":
        try:
            import io

            from PIL import Image

            with Image.open(io.BytesIO(validated.data)) as probe:
                tables = probe.quantization
                if tables:
                    first = tables.get(0) or next(iter(tables.values()))
                    values = [v for v in first if v > 0]
                    if values and (sum(values) / len(values)) < 45:
                        quality_warnings.append({
                            "code": "heavy_compression",
                            "severity": "medium",
                            "en": ("This image appears heavily compressed. "
                                   "Compression artifacts can affect "
                                   "forensic analysis."),
                            "ar": ("تبدو هذه الصورة مضغوطة بشكل كبير. قد تؤثر "
                                   "أثر ضغط الصورة على التحليل الجنائي."),
                        })
        except Exception:  # noqa: BLE001
            pass

    events.append(_timeline("evidence_correlated", f"{len(quality_warnings)} quality flags"))
    events.append(_timeline("trust_assessment_generated", assessment.value))

    duration_ms = round((time.perf_counter() - started) * 1000, 2)

    response = {
        "analysisType": "image",
        "fileName": original_name or validated.stored_name,
        "fileSizeBytes": len(data),
        # NOTE: trustScore is deprecated for image analysis. See canonicalization
        # below (after ensemble/fusion) — it is NOT the user-facing verdict.
        "trustScore": None,
        "riskLevel": risk.risk_level,
        "confidence": risk.confidence,
        # Canonical user-facing assessment. After the ensemble/fusion call below,
        # this is overwritten by the canonical decision so a single research
        # detector can never present "likely_authentic" / trustScore=100 as the
        # authoritative verdict for a known-AI synthetic case.
        "assessment": assessment.value,
        "synthetic": {
            "syntheticProbability": probability,
            "authenticProbability": None if probability is None else round(1 - probability, 6),
            "assessment": assessment.value,
            "uncertain": uncertain,
            "uncertaintyLower": UNCERTAINTY_LOWER,
            "uncertaintyUpper": UNCERTAINTY_UPPER,
        },
        "model": model_status(),
        "metadata": {
            "format": metadata.format,
            "width": metadata.width,
            "height": metadata.height,
            "colorMode": metadata.color_mode,
            "exifPresent": metadata.exif_present,
            "cameraMake": metadata.camera_make,
            "cameraModel": metadata.camera_model,
            "software": metadata.software,
            "createdAt": metadata.created,
            "orientation": metadata.orientation,
            "gpsPresent": metadata.gps_present,
            "interpretationEn": metadata.exif_interpretation,
            "interpretationAr": (
                "لا توجد بيانات EXIF. هذا ليس دليلًا على أن الصورة اصطناعية، "
                "فإن لقطات الشاشة ومنصات التواصل تحذفها عادةً."
                if not metadata.exif_present
                else "توجد بيانات EXIF، وقد تكون من الكاميرا أو من برنامج معالجة."
            ),
        },
        "provenance": {
            "status": ProvenanceStatus(provenance.status).value,
            "contentCredentialsPresent": provenance.content_credentials_present,
            "manifestFound": provenance.manifest_found,
            "limitationEn": provenance.limitation,
            "limitationAr": (
                "لم يتم العثور على بيانات مصدر. معظم الصور لا تحتوي عليها، "
                "بما فيها صور الكاميرا الأصلية التي تُشارَك عبر المنصات. "
                "الغياب ليس دليلًا على المصدر."
            ),
        },
        "forensics": [
            {
                "name": signal.name,
                "value": signal.value,
                "meaningEn": signal.meaning,
                "doesNotMeanEn": signal.does_not_mean,
            }
            for signal in forensics.signals
        ],
        "excludedForensics": forensics.excluded,
        "evidenceQuality": {
            "longEdge": long_edge,
            "lowResolution": long_edge <= LOW_RESOLUTION_LONG_EDGE,
            "warnings": quality_warnings,
        },
        "timeline": events,
        "preprocessing": prepared.to_dict() if model is not None else None,
        "safety": {
            "fitForAutomatedEnforcement": False,
            "status": "research_grade",
            "advisoryOnly": True,
        },
        "durationMs": duration_ms,
    }

    # ---- Legacy detector output. Preserved for diagnostics ONLY as
    # technical data, never as the user-facing verdict.
    raw_assessment = assessment.value
    response["legacyDetector"] = {
        "assessment": raw_assessment,
        "syntheticProbability": probability,
        "authenticProbability": None if probability is None else round(1 - probability, 6),
        "trustScore": risk.trust_score,
        "uncertain": uncertain,
        "advisoryOnly": True,
        "note": "Raw single research-grade detector output. Advisory only. "
                "Does NOT constitute an authenticity verdict.",
    }

    # ---- Phase 3.7: two-detector ensemble + provenance-first tier ------
    # Additive only. Everything above is the pre-3.7 contract and is
    # unchanged, so the existing frontend and tests keep working.
    try:
        response = enrich_with_ensemble(
            response,
            original_bytes=data,
            detector_a_probability=probability,
            long_edge=long_edge,
            warnings=quality_warnings,
        )
    except Exception as exc:  # noqa: BLE001
        # The ensemble is additive. If it fails, the single-detector
        # result is still returned rather than failing the whole request.
        response["ensemble"] = {
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
            "note": (
                "The two-detector ensemble could not run. The single "
                "detector result below is advisory on its own and cannot "
                "support an authenticity claim."
            ),
        }

    # ---- Canonical image decision -------------------------------------------------
    # Make the canonical decision authoritative for USER-FACING fields.
    # A single research-grade detector is NOT allowed to present
    # "likely_authentic" / trustScore=100 as the verdict for a known-AI
    # synthetic case. The canonical result is "uncertain".
    ensemble = response.get("ensemble") or {}
    ensemble_available = ensemble.get("available", True)
    detector_disagreement = ensemble.get("detectorAgreement") == "conflict"
    ensemble_abstained = ensemble.get("abstained", False)
    distribution_status = ensemble.get("distributionStatus")
    evidence_quality = ensemble.get("evidenceQuality")

    canonical = "uncertain"  # default: single research detector can never overclaim
    if ensemble_available:
        if detector_disagreement or ensemble_abstained:
            canonical = "uncertain"
        elif distribution_status == "out_of_distribution":
            canonical = "uncertain"
        elif evidence_quality == "low":
            canonical = "uncertain"
        else:
            # Ensemble ran and did NOT fail. Keep the ensemble outcome as the
            # canonical assessment (it may be likely_synthetic / no_synthetic_indicators).
            canonical = ensemble.get("assessment", "uncertain")

    response["assessment"] = canonical
    response["finalAssessment"] = canonical
    response["trustScore"] = None
    # Canonical "uncertain" is a caution-level result, not a trusted one.
    # The gauge must render "0/100" with a caution colour rather than
    # pretending the image is trusted/authentic.
    response["riskLevel"] = (
        "caution" if canonical == "uncertain" else response.get("riskLevel")
    )
    response["confidence"] = 0.0

    return response
