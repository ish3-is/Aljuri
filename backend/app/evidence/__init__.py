"""Cross-modal correlation middleware for Phase 4.

Detects relationships between evidence items and produces correlation
findings. All correlations are traceable to evidence IDs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evidence.model import EvidenceEntity, Polarity
from app.evidence.relationship import Relationship

CONFLICT_TYPES = {
    "displayed_destination_mismatch": "DISPLAYED_DESTINATION_MISMATCH",
    "url_domain_mismatch": "URL_DOMAIN_MISMATCH",
    "qr_url_mismatch": "QR_URL_MISMATCH",
    "c2pa_detector_conflict": "C2PA_DETECTOR_CONFLICT",
    "file_extension_mismatch": "FILE_EXTENSION_MISMATCH",
    "metadata_origin_inconsistency": "METADATA_ORIGIN_INCONSISTENCY",
    "encoding_decodes_to_url": "ENCODING_DECODES_TO_URL",
    "qr_vs_ocr_url": "QR_VS_OCR_URL",
}


@dataclass
class CorrelationFinding:
    conflict_type: str
    evidence_a: str
    evidence_b: str
    severity: str = "high"
    explanation: str = ""
    entities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflictType": self.conflict_type,
            "evidenceA": self.evidence_a,
            "evidenceB": self.evidence_b,
            "severity": self.severity,
            "explanation": self.explanation,
            "entities": self.entities,
        }


def _safe_str(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, dict):
        return str(value)[:80]
    return str(value)[:80]


def _looks_like_domain(text: str) -> bool:
    import re
    if not text or len(text) < 3:
        return False
    return bool(re.match(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", text.lower().strip()))


def correlate_evidence(entities: list[EvidenceEntity], relationships: list[Relationship]) -> list[dict[str, Any]]:
    """Correlate evidence across modalities."""
    findings: list[CorrelationFinding] = []
    entity_map = {e.id: e for e in entities}

    for rel in relationships:
        a = entity_map.get(rel.from_entity)
        b = entity_map.get(rel.to_entity)
        if not a or not b:
            continue

        if rel.relation == "points_to":
            b_entity = entity_map.get(rel.to_entity)
            if b_entity and b_entity.type == "URL":
                if b_entity.normalized and _looks_like_domain(b_entity.normalized):
                    if a.polarity == Polarity.SUPPORTS_RISK and b_entity.confidence:
                        findings.append(CorrelationFinding(
                            conflict_type=CONFLICT_TYPES["displayed_destination_mismatch"],
                            evidence_a=a.id,
                            evidence_b=b_entity.id,
                            severity="high" if b_entity.confidence > 0.8 else "medium",
                            explanation="Displayed identity and extracted destination differ.",
                            entities=[a.id, b_entity.id],
                        ))

        elif rel.relation == "decoded_from":
            a_entity = entity_map.get(rel.from_entity)
            b_entity = entity_map.get(rel.to_entity)
            if a_entity and b_entity:
                if a_entity.type == "EncodedPayload" and b_entity.type == "URL":
                    findings.append(CorrelationFinding(
                        conflict_type=CONFLICT_TYPES["encoding_decodes_to_url"],
                        evidence_a=a_entity.id,
                        evidence_b=b_entity.id,
                        severity="high",
                        explanation="Encoded content decodes into a destination.",
                        entities=[a_entity.id, b_entity.id],
                    ))

        elif rel.relation == "displayed_as":
            a_entity = entity_map.get(rel.from_entity)
            b_entity = entity_map.get(rel.to_entity)
            if a_entity and b_entity:
                if a_entity.type == "VisibleDomain" and b_entity.type == "URL":
                    if a_entity.normalized and a_entity.normalized != b_entity.normalized:
                        findings.append(CorrelationFinding(
                            conflict_type=CONFLICT_TYPES["displayed_destination_mismatch"],
                            evidence_a=a_entity.id,
                            evidence_b=b_entity.id,
                            severity="high" if a_entity.confidence and b_entity.confidence else "medium",
                            explanation="Displayed identity and destination differ.",
                            entities=[a_entity.id, b_entity.id],
                        ))

    return [f.to_dict() for f in findings]
