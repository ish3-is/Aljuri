"""
Image analysis response schemas.

These mirror the URL analysis contract in shape so the frontend can render
both through the same result experience, while keeping image-specific
evidence honest and separate.

The critical semantic choice: there is no `isFake` boolean anywhere in
this contract, and no field that could be trivially collapsed into one.
The frontend receives a probability, a three-way assessment category, an
uncertainty band, and the evidence channels that produced it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Assessment(str, Enum):
    """Three-way, never binary.

    ``UNCERTAIN`` is a first-class outcome. A detector that must answer
    yes/no will guess in the middle band; naming the band makes the
    refusal explicit.
    """

    LIKELY_SYNTHETIC = "likely_synthetic"
    UNCERTAIN = "uncertain"
    LIKELY_AUTHENTIC = "likely_authentic"


class ProvenanceState(str, Enum):
    VERIFIED = "verified"
    PRESENT_UNVERIFIED = "present_unverified"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


class EvidenceChannel(BaseModel):
    """One independent way of knowing something about the image."""

    name: str
    #: Human-readable summary, already phrased as evidence not verdict.
    summary_en: str
    summary_ar: str
    #: Explicitly what this channel cannot establish.
    limitation_en: str | None = None
    limitation_ar: str | None = None
    #: One of: primary, corroborating, weak, none.
    weight: str = "weak"


class ImageMetadataResponse(BaseModel):
    format: str
    width: int
    height: int
    colorMode: str
    exifPresent: bool
    cameraMake: str | None = None
    cameraModel: str | None = None
    software: str | None = None
    createdAt: str | None = None
    orientation: int | None = None
    #: Boolean only. GPS coordinates are never returned by design.
    gpsPresent: bool = False
    interpretation_en: str
    interpretation_ar: str


class ProvenanceResponse(BaseModel):
    status: ProvenanceState
    contentCredentialsPresent: bool
    manifestFound: bool = False
    limitation_en: str
    limitation_ar: str


class ForensicSignalResponse(BaseModel):
    name: str
    value: float | None
    meaning_en: str
    doesNotMean_en: str


class SyntheticModelResponse(BaseModel):
    modelName: str | None = None
    modelVersion: str | None = None
    available: bool
    reason: str | None = None
    syntheticProbability: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="P(synthetic). 1.0 means confidently synthetic.",
    )
    authenticProbability: float | None = Field(default=None, ge=0.0, le=1.0)
    assessment: Assessment
    #: True when the probability sits inside the calibrated uncertain band.
    uncertain: bool
    threshold: float | None = None
    #: Advisory only. No image model in this project is cleared for action.
    fitForAutomatedEnforcement: bool = False


class ImageAnalysisResponse(BaseModel):
    """Contract for POST /api/analyze/image."""

    model_config = {"populate_by_name": True}

    # Echoed back for the report header; never used for filesystem access.
    fileName: str
    fileSizeBytes: int

    # Headline, 0-100, higher = more trustworthy.
    trustScore: float = Field(ge=0.0, le=100.0)
    riskLevel: str
    confidence: float = Field(ge=0.0, le=100.0)

    synthetic: SyntheticModelResponse
    metadata: ImageMetadataResponse | None = None
    provenance: ProvenanceResponse
    forensics: list[ForensicSignalResponse] = Field(default_factory=list)
    evidenceChannels: list[EvidenceChannel] = Field(default_factory=list)

    primarySignalEn: str
    primarySignalAr: str
    secondarySignalsEn: list[str] = Field(default_factory=list)
    secondarySignalsAr: list[str] = Field(default_factory=list)

    #: Always populated. What this analysis did NOT do.
    limitationsEn: list[str] = Field(default_factory=list)
    limitationsAr: list[str] = Field(default_factory=list)

    durationMs: float
