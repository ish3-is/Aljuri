"""Relationship engine for Phase 4.

All relationships are traceable to actual evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

RELATIONS = {
    "contains": "contains",
    "extracted_from": "extracted_from",
    "points_to": "points_to",
    "redirects_to": "redirects_to",
    "displayed_as": "displayed_as",
    "conflicts_with": "conflicts_with",
    "supports": "supports",
    "contradicts": "contradicts",
    "signed_by": "signed_by",
    "generated_by": "generated_by",
    "edited_by": "edited_by",
    "decoded_from": "decoded_from",
    "mentioned_in": "mentioned_in",
    "correlates_with": "correlates_with",
}


@dataclass
class Relationship:
    id: str
    from_entity: str
    to_entity: str
    relation: str
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float | None = None
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_entity,
            "to": self.to_entity,
            "relation": self.relation,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "severity": self.severity,
        }
