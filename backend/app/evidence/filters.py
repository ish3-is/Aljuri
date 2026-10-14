"""Evidence filters for Phase 4.

Classifies evidence by category: Verified, Model, Heuristic, Risk, Trust, Conflict, Unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

class FilterKind(str, Enum):
    VERIFIED = "verified"
    MODEL = "model"
    HEURISTIC = "heuristic"
    RISK = "risk"
    TRUST = "trust"
    CONFLICT = "conflict"
    UNAVAILABLE = "unavailable"


@dataclass
class EvidenceFilter:
    kind: FilterKind
    label: str
    description: str
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "description": self.description,
            "active": self.active,
        }
