"""Unified evidence model for Phase 4 multimodal intelligence.

One normalized representation for every evidence modality.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Polarity(str, Enum):
    SUPPORTS_RISK = "supports_risk"
    SUPPORTS_TRUST = "supports_trust"
    NEUTRAL = "neutral"
    UNCERTAIN = "uncertain"


class Strength(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEUTRAL = "neutral"


@dataclass
class EvidenceEntity:
    id: str
    source: str
    modality: str
    type: str
    title: str
    description: str = ""
    rawValue: Any = None
    normalizedValue: Any = None
    confidence: float | None = None
    severity: str | None = None
    polarity: Polarity = Polarity.NEUTRAL
    evidenceStrength: Strength = Strength.LOW
    verified: bool = False
    relatedEntities: list[str] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stage: str = "extraction"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "modality": self.modality,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "rawValue": self.rawValue,
            "normalizedValue": self.normalizedValue,
            "confidence": self.confidence,
            "severity": self.severity,
            "polarity": self.polarity.value if self.polarity else None,
            "evidenceStrength": self.evidenceStrength.value if self.evidenceStrength else None,
            "verified": self.verified,
            "relatedEntities": self.relatedEntities,
            "relationships": self.relationships,
            "limitations": self.limitations,
            "timestamp": self.timestamp,
            "stage": self.stage,
        }
