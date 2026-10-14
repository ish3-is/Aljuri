"""Visible domain extraction from OCR text.

Detects domain-like text visible in OCR output. Conservative: no
aggressive correction of uncertain OCR.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.evidence.model import EvidenceEntity, Polarity, Strength

DOMAIN_RE = re.compile(r"(?<![a-zA-Z0-9-])([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}", re.I)
SMTP_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)
IPV4_RE = re.compile(r"(?<!\d)((?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?!\d)")


@dataclass
class VisibleDomain:
    raw: str
    domain: str
    confidence: float
    source: str = "ocr"

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "domain": self.domain,
            "confidence": self.confidence,
            "source": self.source,
        }


def extract_visible_domains(text: str, source: str = "ocr", confidence: float = 0.8) -> list[VisibleDomain]:
    """Extract domain-like text from OCR output. Conservative, no aggressive correction."""
    domains: list[VisibleDomain] = []
    seen: set[str] = set()

    for match in DOMAIN_RE.finditer(text):
        raw = match.group(0)
        domain = raw.lower().strip()
        if domain in seen:
            continue
        seen.add(domain)
        domains.append(VisibleDomain(raw=raw, domain=domain, confidence=confidence, source=source))

    return domains


def extract_visible_text_domains(ocr_text: str, engine: str = "tesseract") -> list[EvidenceEntity]:
    """Convert visible domains into EvidenceEntities with uncertainty tracking."""
    entities: list[EvidenceEntity] = []
    for i, vd in enumerate(extract_visible_domains(ocr_text)):
        eid = f"vd-{engine}-{i:03d}"
        entities.append(EvidenceEntity(
            id=eid,
            source=engine,
            modality="ocr",
            type="VisibleDomain",
            title=f"Visible domain: {vd.domain}",
            description=f"Raw visible text: {vd.raw}",
            normalizedValue=vd.domain,
            rawValue=vd.raw,
            confidence=vd.confidence,
            severity="medium",
            polarity=Polarity.NEUTRAL,
            evidenceStrength=Strength.MEDIUM,
            verified=False,
            limitations=[] if vd.confidence > 0.7 else ["Low-confidence OCR; domain may not be exact."],
            stage="extraction",
        ))
    return entities
