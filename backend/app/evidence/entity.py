"""Evidence entity model for Phase 4.

Normalized entities for every evidence type. Entities are only created
from high-confidence OCR; low-confidence OCR does not fabricate entities.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    id: str
    type: str
    display: str = ""
    normalized: str = ""
    source: str = ""
    confidence: float | None = None
    uncertainty: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "display": self.display,
            "normalized": self.normalized,
            "source": self.source,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
        }
