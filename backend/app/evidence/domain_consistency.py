"""Domain consistency and IDN/homoglyph awareness for Phase 4.

Conservatively detects punycode, mixed scripts and confusable indicators
without claiming maliciousness.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.evidence.model import EvidenceEntity, Polarity, Strength

PUNYCODE_RE = re.compile(r'xn--[a-z0-9-]+', re.I)
IDN_INDICATOR_RE = re.compile(r'[^\x00-\x7F]')
LTR_RE = re.compile(r'[A-Za-z0-9]')
RTL_RE = re.compile(r'[\\u0600-\\u06FF\\u0750-\\u077F\\u0800-\\u083F]', re.I)


@dataclass
class DomainConsistency:
    status: str
    canonical: str = ""
    punycode_present: bool = False
    mixed_script: bool = False
    confusable_indicator: bool = False
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "canonical": self.canonical,
            "punycodePresent": self.punycode_present,
            "mixedScript": self.mixed_script,
            "confusableIndicator": self.confusable_indicator,
            "limitations": self.limitations,
        }


def _canonical_host(host: str) -> str:
    return host.lower().rstrip('.')


def _is_punycode(host: str) -> bool:
    return bool(PUNYCODE_RE.search(host))


def _has_mixed_script(host: str) -> bool:
    has_ltr = False
    has_rtl = False
    for ch in host:
        if LTR_RE.match(ch):
            has_ltr = True
        if RTL_RE.match(ch):
            has_rtl = True
    return has_ltr and has_rtl


def check_domain_consistency(domains: list[str]) -> DomainConsistency:
    hosts = [_canonical_host(d) for d in domains if d]
    if not hosts:
        return DomainConsistency(status="insufficient_evidence", limitations=["No domain candidates found."])

    canonical = hosts[0]
    for h in hosts[1:]:
        if h != canonical:
            canonical = "mismatch"

    punycode_present = any(_is_punycode(h) for h in hosts)
    mixed_script = any(_has_mixed_script(h) for h in hosts)

    if canonical == "mismatch":
        status = "mismatch"
    elif len(hosts) == 1:
        status = "consistent"
    else:
        status = "partially_consistent"

    return DomainConsistency(
        status=status,
        canonical=canonical,
        punycode_present=punycode_present,
        mixed_script=mixed_script,
        confusable_indicator=punycode_present or mixed_script,
        limitations=[] if not (punycode_present or mixed_script) else ["IDN/homoglyph indicators present; not automatically malicious."],
    )


def extract_domain_entities(visible_domains: list[dict], engine: str = "ocr") -> list[EvidenceEntity]:
    entities = []
    for i, vd in enumerate(visible_domains):
        eid = f"domain-{engine}-{i:03d}"
        entities.append(EvidenceEntity(
            id=eid,
            source=engine,
            modality="ocr",
            type="Domain",
            title=f"Domain: {vd.get('domain', '')}",
            description=f"Raw: {vd.get('raw', '')}",
            normalizedValue=vd.get('domain'),
            rawValue=vd.get('raw'),
            confidence=vd.get('confidence'),
            severity="medium",
            polarity=Polarity.NEUTRAL,
            evidenceStrength=Strength.MEDIUM,
            verified=False,
            limitations=[] if vd.get('confidence', 0) > 0.7 else ["Low-confidence OCR detected this domain."],
            stage="extraction",
        ))
    return entities


def extract_homoglyph_entities(host: str, engine: str = "domain") -> list[EvidenceEntity]:
    entities = []
    punycode_present = _is_punycode(host)
    mixed_script = _has_mixed_script(host)

    if punycode_present:
        entities.append(EvidenceEntity(
            id=f"idn-puny-{engine}",
            source=engine,
            modality="domain",
            type="PunycodeIndicator",
            title="Punycode present in hostname",
            description=f"Hostname contains punycode: {host[:60]}",
            normalizedValue=host,
            confidence=0.9,
            severity="low",
            polarity=Polarity.UNCERTAIN,
            evidenceStrength=Strength.LOW,
            verified=False,
            limitations=["Punycode present; not automatically malicious."],
            stage="extraction",
        ))

    if mixed_script:
        entities.append(EvidenceEntity(
            id=f"idn-mixed-{engine}",
            source=engine,
            modality="domain",
            type="MixedScriptIndicator",
            title="Mixed-script hostname detected",
            description=f"Hostname contains multiple scripts: {host[:80]}",
            normalizedValue=host,
            confidence=0.85,
            severity="low",
            polarity=Polarity.UNCERTAIN,
            evidenceStrength=Strength.LOW,
            verified=False,
            limitations=["Mixed-script; does not imply maliciousness."],
            stage="extraction",
        ))

    return entities
