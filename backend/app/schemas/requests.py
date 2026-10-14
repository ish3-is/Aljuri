"""Request schemas for the BASIRAH API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class URLAnalysisRequest(BaseModel):
    """A URL submitted for analysis.

    Length is bounded here as well as in the normalizer: Pydantic rejects
    an oversized payload before it reaches any service, which is cheaper
    and safer than validating inside the analyser.
    """

    url: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_url_length,
        description="The URL to analyse. Scheme is optional.",
        json_schema_extra={"example": "https://example.com"},
    )

    @field_validator("url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("URL must not be blank.")
        return value


class URLEngineInfo(BaseModel):
    """URL-specific metrics, nested for forward compatibility."""

    model_available: bool
    heuristic_rules: int
    feature_count: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    phase: str
    model_available: bool
    url_engine: URLEngineInfo
