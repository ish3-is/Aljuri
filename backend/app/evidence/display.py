"""Confidence and display indicators for Phase 4.

Use Verified / Strong / Moderate / Weak / Uncertain - not misleading red/green percentages.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONFIDENCE_LEVELS = [
    ("verified", "Verified", "High confidence; cross-checked against independent sources."),
    ("strong", "Strong", "High confidence; consistent with related evidence."),
    ("moderate", "Moderate", "Medium confidence; some uncertainty remains."),
    ("weak", "Weak", "Low confidence; treat as indicative only."),
    ("uncertain", "Uncertain", "No reliable conclusion; evidence is conflicting or missing."),
]


@dataclass
class ConfidenceDisplay:
    level: str
    label: str
    description: str
    color: str

    @classmethod
    def from_level(cls, level: str) -> "ConfidenceDisplay":
        for lvl, label, desc in CONFIDENCE_LEVELS:
            if lvl == level:
                return cls(lvl, label, desc,
                           {"verified": "var(--color-trusted)",
                            "strong": "var(--color-signal)",
                            "moderate": "var(--color-caution)",
                            "weak": "var(--color-danger)",
                            "uncertain": "var(--color-line)"}[lvl])
        return cls("uncertain", "Uncertain", "No reliable conclusion.", "var(--color-line)")

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "label": self.label,
            "description": self.description,
            "color": self.color,
        }
