"""HTTP routes for the BASIRAH URL Intelligence Engine."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.image.model_loader import model_status as image_model_status
from app.image.service import analyze_image
from app.image.validation import ImageValidationError
from app.ml.model_readiness import health_readiness
from app.ml.production import production_status, safety_status
from app.ml.feature_schema import model_feature_names
from app.schemas.requests import HealthResponse, URLEngineInfo, URLAnalysisRequest
from app.schemas.responses import ModelInfoResponse, URLAnalysisResponse
from app.services.analyzer import URLAnalysisError, analyze_url
from app.services.feature_extractor import FEATURE_NAMES
from app.services.heuristic_engine import RULES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness plus honest reporting of which components are active."""
    readiness = health_readiness()
    # `lfs: dict[str, bool]` maps each runtime model to its availability.
    # The aggregate boolean `ready` is the deployment decision for startup;
    # the per-model detail is what the API consumer reads.
    return HealthResponse(
        status="ok",
        service="BASIRAH Digital Trust Intelligence",
        version=settings.version,
        phase="Phase 4 — Multimodal Intelligence",
        model_available=production_status()[0],
        lfs={name: m["available"] for name, m in readiness["models"].items()},
        url_engine=URLEngineInfo(
            model_available=production_status()[0],
            heuristic_rules=len(RULES),
            feature_count=len(FEATURE_NAMES),
        ),
    )


@router.post(
    "/analyze/url",
    response_model=URLAnalysisResponse,
    tags=["analysis"],
    summary="Analyse a URL with the local URL intelligence pipeline",
)
def analyze_url_endpoint(
    payload: URLAnalysisRequest,
) -> URLAnalysisResponse | JSONResponse:
    """Analyse one URL.

    Returns 422 for input we refuse to analyse (unsupported scheme,
    oversized, unparsable) with a stable machine-readable `code`, so the
    frontend can distinguish a bad request from a server fault.
    """
    try:
        return analyze_url(payload.url)
    except URLAnalysisError as exc:
        logger.info("Rejected URL (%s): %s", exc.payload.code, exc.payload.detail)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=exc.payload.model_dump(),
        )


@router.get(
    "/model/info",
    response_model=ModelInfoResponse,
    tags=["system"],
    summary="Model transparency metadata",
)
def model_info() -> ModelInfoResponse:
    """Report which model is loaded and how it performed in training.

    Returns no filesystem paths, and null metrics rather than invented
    ones when no model has been trained. `metrics` is the grouped-domain
    (production) evaluation, which is the honest headline number.
    """
    available, reason, meta = production_status()
    safety = safety_status()

    # Prefer the grouped-domain metrics: that is the split the model was
    # selected on. `metrics_random_split` is retained in the full metadata
    # but is the optimistic number, so it is not what gets served here.
    metrics = meta.get("metrics_grouped_domain")
    if not isinstance(metrics, dict):
        metrics = meta.get("metrics")
    if not isinstance(metrics, dict):
        metrics = None

    # v3 metadata stores the column list as "feature_names"; Phase 2B used
    # "features". Accept either, and fall back to the live schema rather
    # than the full extractor output, which includes the two excluded
    # scheme features and would misreport the model's input width.
    feature_names = meta.get("feature_names") or meta.get("features")
    if not isinstance(feature_names, list) or not feature_names:
        feature_names = model_feature_names()

    payload = ModelInfoResponse(
        available=available,
        reason=reason,
        modelName=meta.get("model_name"),  # type: ignore[arg-type]
        modelVersion=meta.get("model_version"),  # type: ignore[arg-type]
        featureCount=len(feature_names),  # type: ignore[arg-type]
        features=feature_names,  # type: ignore[arg-type]
        metrics=metrics,  # type: ignore[arg-type]
        datasetRows=meta.get("rows_used") or meta.get("dataset_rows"),  # type: ignore[arg-type]
        trainedAt=meta.get("trained_at"),  # type: ignore[arg-type]
    )
    # Safety and provenance are attached dynamically so the response
    # schema stays backward compatible for existing frontend consumers.
    for key, value in safety.items():
        setattr(payload, key, value)
    for key in ("training_corpora", "held_out_corpora", "selected_threshold", "selected_configuration"):
        if key in meta:
            setattr(payload, key, meta[key])
    return payload


# ====================================================================
# IMAGE INTELLIGENCE (Phase 3.5)
# ====================================================================
# Research-grade only. Every response carries the advisory flags, and no
# response ever falls back to a fabricated probability when the model is
# unavailable - an honest "unavailable" is more useful than a confident
# number the model cannot support.

IMAGE_MAX_BYTES = 15 * 1024 * 1024

# The multimodal endpoint accepts text-like files too, which are far
# smaller than images; the ceiling stays at the image limit so the
# in-memory read bound is unchanged.
EVIDENCE_MAX_BYTES = 15 * 1024 * 1024


@router.post(
    "/analyze/evidence",
    tags=["analysis"],
    summary="Multimodal evidence analysis (image, screenshot or text file).",
)
async def analyze_evidence_endpoint(
    file: UploadFile = File(..., description="Image, screenshot or text-like file."),
    mode: str = Query("auto", pattern="^(auto|image|screenshot|file)$"),
) -> JSONResponse:
    """
    Analyse one upload across every applicable modality.

    Orchestrates validation, provenance, the image ensemble, OCR, QR,
    URL extraction, URL intelligence, encoding inspection, metadata,
    forensics and evidence fusion into a single normalised response.

    Additive: /analyze/image and /analyze/url are unchanged.
    """
    from app.evidence_service import analyze_evidence

    data = await file.read()
    if not data:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"code": "empty_file",
                     "detail": "The uploaded file was empty."},
        )
    if len(data) > EVIDENCE_MAX_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"code": "file_too_large",
                     "detail": "File exceeds the inspection size limit."},
        )

    result = await run_in_threadpool(
        analyze_evidence,
        data,
        filename=file.filename,
        content_type=file.content_type,
        mode=mode,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=result)


@router.post(
    "/analyze/image",
    tags=["analysis"],
    summary="Analyse an uploaded image for synthetic-media indicators (advisory).",
)
async def analyze_image_endpoint(
    file: UploadFile = File(..., description="JPEG, PNG or WEBP image."),
) -> JSONResponse:
    payload = await file.read()

    if len(payload) > IMAGE_MAX_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "error": f"File exceeds the {IMAGE_MAX_BYTES // (1024 * 1024)} MB limit.",
                "code": "file_too_large",
            },
        )

    try:
        result = analyze_image(
            payload,
            original_name=file.filename,
            content_type=file.content_type,
        )
    except ImageValidationError as exc:
        # 400 for a bad file, 415 for a format we do not analyse. The
        # distinction matters: "this is not an image" and "this format is
        # out of scope" are different messages to a user.
        status = 415 if exc.code in {
            "unsupported_format", "svg_not_supported"
        } else 400
        return JSONResponse(
            status_code=status, content={"error": str(exc), "code": exc.code}
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("image analysis failed")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Image analysis could not be completed.",
                "code": "analysis_failed",
                "detail": type(exc).__name__,
            },
        )

    return JSONResponse(status_code=200, content=result)


@router.get("/model/image/info", tags=["system"], summary="Image model status.")
async def image_model_info() -> JSONResponse:
    """Exposes the research-grade status. Contains no filesystem paths."""
    from app.image.model_loader import model_status as _status

    payload = _status()
    payload.pop("checkpoint", None)
    return JSONResponse(status_code=200, content=payload)
