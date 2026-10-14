"""Content coverage model for Phase 4.

Explicit analysis coverage per modality. Coverage is not trust.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CoverageModel:
    image_pixels: int = 0
    provenance: str = "not_applicable"
    ocr: str = "not_applicable"
    qr: str = "not_applicable"
    url: str = "not_applicable"
    encoding: str = "not_applicable"
    file_structure: str = "not_applicable"
    forensic_signals: int = 0
    total_entities: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "imagePixels": self.image_pixels,
            "provenance": self.provenance,
            "ocr": self.ocr,
            "qr": self.qr,
            "url": self.url,
            "encoding": self.encoding,
            "fileStructure": self.file_structure,
            "forensicSignals": self.forensic_signals,
            "totalEntities": self.total_entities,
        }

    def coverage_percent(self) -> float:
        measured = sum(1 for v in [self.provenance, self.ocr, self.qr, self.url, self.encoding] if v != "not_applicable")
        return round((measured / 5) * 100, 1)
