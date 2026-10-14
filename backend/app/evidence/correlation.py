"""Correlation service for Phase 4.

Builds the evidence graph, timeline, and correlation findings from the
raw evidence endpoint payload.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from app.evidence.domain_consistency import check_domain_consistency, extract_homoglyph_entities
from app.evidence.entity import Entity
from app.evidence.model import EvidenceEntity, Polarity
from app.evidence.relationship import Relationship
from app.evidence.visible_domain import extract_visible_domains
from app.evidence.relationship import RELATIONS
from app.evidence.coverage import CoverageModel


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_str(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, dict):
        return str(value)[:120]
    return str(value)[:120]


def _looks_like_domain(text: str) -> bool:
    import re
    if not text or len(text) < 3:
        return False
    return bool(re.match(r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$", text.lower().strip()))


def build_evidence_graph(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a normalized evidence graph from the evidence payload."""
    entities: list[EvidenceEntity] = []
    evidence_ids: list[str] = []

    def add_entity(e: EvidenceEntity) -> str:
        eid = e.id
        entities.append(e)
        if eid not in evidence_ids:
            evidence_ids.append(eid)
        return eid

    # The payload structure from evidence_service
    ocr = payload.get("ocr")
    qr = payload.get("qr")
    urls = payload.get("urls") or []
    file_finding = payload.get("file") or {}
    encoding_findings = payload.get("encoding") or []
    provenance = payload.get("provenance") or {}

    # Input evidence
    add_entity(EvidenceEntity(
        id="input",
        source="input",
        modality=payload.get("mode", "unknown"),
        type="Input",
        title="Input upload",
        rawValue=_safe_str(payload.get("fileName")),
        confidence=1.0,
        verified=True,
        stage="acquisition",
    ))

    # Provenance
    if provenance:
        add_entity(EvidenceEntity(
            id="provenance",
            source="provenance",
            modality="provenance",
            type="Provenance",
            title="Content Credentials",
            rawValue=provenance.get("status"),
            normalizedValue=provenance.get("standard"),
            confidence=0.9 if provenance.get("status") == "verified" else 0.3,
            severity="medium",
            polarity=(Polarity.SUPPORTS_TRUST if provenance.get("status") == "verified" else Polarity.UNCERTAIN),
            evidenceStrength=(Polarity.SUPPORTS_TRUST if provenance.get("status") == "verified" else Polarity.UNCERTAIN),
            verified=(provenance.get("status") == "verified"),
            limitations=provenance.get("notes", []),
            stage="verification",
        ))

    # Image detail
    image = payload.get("image")
    if image:
        add_entity(EvidenceEntity(
            id="image_analysis",
            source="image",
            modality="image",
            type="ImageAnalysis",
            title="Image analysis",
            rawValue=None,
            normalizedValue=None,
            confidence=None,
            stage="verification",
        ))

    # Ensemble
    ens = payload.get("ensemble")
    if ens:
        add_entity(EvidenceEntity(
            id="ensemble",
            source="ensemble",
            modality="image",
            type="DetectorEnsemble",
            title="Detector agreement",
            rawValue=ens.get("detectorAgreement"),
            normalizedValue=None,
            confidence=None,
            stage="correlation",
        ))

    # OCR entities
    if ocr and isinstance(ocr, dict):
        add_entity(EvidenceEntity(
            id="ocr",
            source="ocr",
            modality="ocr",
            type="OCR",
            title="OCR text",
            rawValue=str(ocr.get("text", ""))[:200],
            normalizedValue=ocr.get("normalizedText"),
            confidence=ocr.get("confidence"),
            stage="extraction",
        ))
        for url_entry in ocr.get("urls") or []:
            if url_entry.get("normalizedCandidate"):
                add_entity(EvidenceEntity(
                    id=f"ocr_url_{url_entry.get('origin', '')}",
                    source="ocr",
                    modality="ocr",
                    type="URL",
                    title=f"URL from OCR: {url_entry.get('normalizedCandidate', '')[:80]}",
                    rawValue=url_entry.get("rawExtractedText"),
                    normalizedValue=url_entry.get("normalizedCandidate"),
                    confidence=url_entry.get("confidence"),
                    stage="extraction",
                ))

    # QR entities
    if qr and isinstance(qr, dict):
        add_entity(EvidenceEntity(
            id="qr",
            source="qr",
            modality="qr",
            type="QR",
            title="QR code",
            rawValue=qr.get("payload"),
            normalizedValue=None,
            confidence=0.9 if qr.get("payload") else 0.0,
            stage="extraction",
        ))
        if qr.get("payload") and qr.get("isUrl"):
            add_entity(EvidenceEntity(
                id="qr_url",
                source="qr",
                modality="qr",
                type="URL",
                title=f"QR URL: {str(qr.get('payload', ''))[:80]}",
                rawValue=qr.get("payload"),
                normalizedValue=str(qr.get("payload")),
                confidence=0.95,
                stage="extraction",
            ))

    # URL entities
    for i, entry in enumerate(urls):
        if entry.get("normalizedCandidate"):
            add_entity(EvidenceEntity(
                id=f"url_{i:03d}",
                source="url_intelligence",
                modality="url_intelligence",
                type="URL",
                title=f"URL: {str(entry.get('normalizedCandidate', ''))[:80]}",
                rawValue=entry.get("rawExtractedText"),
                normalizedValue=entry.get("normalizedCandidate"),
                confidence=entry.get("confidence", 0.7),
                severity=entry.get("urlIntelligence", {}).get("riskLevel", "medium"),
                polarity=Polarity.SUPPORTS_RISK if entry.get("urlIntelligence", {}).get("riskLevel") == "high_risk" else Polarity.NEUTRAL,
                evidenceStrength=Polarity.HIGH if entry.get("urlIntelligence", {}).get("riskLevel") == "high_risk" else Polarity.LOW,
                verified=False,
                stage="correlation",
            ))
            ui = entry.get("urlIntelligence") or {}
            if ui.get("riskLevel") == "high_risk":
                add_entity(EvidenceEntity(
                    id=f"url_{i:03d}_risk",
                    source="url_intelligence",
                    modality="url_intelligence",
                    type="RiskSignal",
                    title=f"High-risk destination: {str(entry.get('normalizedCandidate', ''))[:80]}",
                    rawValue=None,
                    normalizedValue=str(entry.get('normalizedCandidate')),
                    confidence=ui.get("confidence"),
                    severity=ui.get("riskLevel"),
                    polarity=(Polarity.SUPPORTS_RISK if ui.get("riskLevel") == "high_risk" else Polarity.NEUTRAL),
                    evidenceStrength=Strength.HIGH,
                    verified=False,
                    stage="correlation",
                ))

    # Encoding entities
    for i, enc in enumerate(encoding_findings):
        if enc.get("decodedPreview"):
            add_entity(EvidenceEntity(
                id=f"encoding_{i}",
                source="file_intelligence",
                modality="encoding",
                type="EncodedPayload",
                title="Encoded content decoded",
                rawValue=enc.get("rawPreview"),
                normalizedValue=enc.get("decodedPreview"),
                confidence=enc.get("confidence", 0.8),
                stage="extraction",
            ))
            # Relationship: decoded_from
            if enc.get("decodedPreview") and any(e.id == f"url_{i:03d}" for e in entities):
                pass  # URL already added

    # File entities
    if file_finding and isinstance(file_finding, dict):
        if file_finding.get("accepted"):
            add_entity(EvidenceEntity(
                id="file",
                source="file_intelligence",
                modality="file_intelligence",
                type="File",
                title=f"File: {str(file_finding.get('fileKind', ''))}",
                rawValue=file_finding.get("sizeBytes"),
                normalizedValue=f"{file_finding.get('textChars')} chars",
                confidence=0.8,
                stage="extraction",
            ))

    # Build relationships
    relationships: list[Relationship] = []
    rel_id = 0

    def add_rel(src: str, tgt: str, rel: str, evidence_refs: list[str] = None) -> None:
        nonlocal rel_id
        rel_id += 1
        relationships.append(Relationship(
            id=f"rel_{rel_id:04d}",
            from_entity=src,
            to_entity=tgt,
            relation=rel,
            evidence_refs=evidence_refs or [],
            confidence=0.8,
            severity="medium",
        ))

    # Input -> each evidence item
    for e in entities:
        if e.id == "input":
            continue
        add_rel("input", e.id, "contains", [e.id])

    # Provenance relationships
    if provenance:
        if provenance.get("aiGeneratedAssertion") is True:
            add_rel("provenance", "ensemble", "signed_by", [])
        if provenance.get("manifestPresent"):
            add_rel("provenance", "input", "signed_by", [])
            add_rel("provenance", "image_analysis", "signed_by", [])

    # OCR -> URLs
    for e in entities:
        if e.type == "URL" and e.source == "ocr":
            add_rel("ocr", e.id, "extracts", [])
            # Find visible domain, if present
            visible_domains = extract_visible_domains(str(ocr.get("text", "")) if ocr else "")
            for vd in visible_domains:
                dom_e = next((x for x in entities if x.type == "VisibleDomain" and x.id.startswith("vd-")), None)
                if dom_e:
                    add_rel(dom_e.id, e.id, "displayed_as", [])

    # QR -> URL
    if qr and isinstance(qr, dict):
        if qr.get("payload") and qr.get("isUrl"):
            qr_url_entity = next((e for e in entities if e.type == "URL" and e.id == "qr_url"), None)
            if qr_url_entity:
                add_rel("qr", "qr_url", "decoded_from", [])
                add_rel("qr_url", "input", "points_to", [])

    # URL -> QR correlation
    for e in entities:
        if e.type == "URL":
            qr_entity = next((e2 for e2 in entities if e2.type == "QR" and e2.id == "qr"), None)
            if qr_entity and e.source == "url_intelligence":
                add_rel(e.id, "qr", "compares_with", [])

    # Build node/edge lists
    nodes = []
    for e in entities:
        nodes.append({
            "id": e.id,
            "labelEn": e.title,
            "labelAr": f"{e.title} ({e.type})",
            "detailEn": f"{e.source}: {str(e.rawValue)[:100]}",
            "detailAr": f"{e.source}: {str(e.rawValue)[:100]}",
            "weight": "primary" if e.evidenceStrength in ("very_high", "high") else "secondary",
            "polarity": e.polarity.value if e.polarity else "neutral",
            "x": 20 + (hash(e.id) % 60),
            "y": 20 + (hash(e.id) % 60),
        })

    edges = []
    for r in relationships:
        edges.append({
            "from": r.from_entity,
            "to": r.to_entity,
            "relation": r.relation,
        })

    # Cross-modal correlation
    correlations = run_correlation(entities, relationships)

    coverage = CoverageModel(
        image_pixels=len(payload.get("data", b"") or b""),
        provenance="available" if payload.get("provenance") else "not_applicable",
        ocr="analyzed" if payload.get("ocr") else "not_applicable",
        qr="analyzed" if payload.get("qr") else "not_applicable",
        url="analyzed" if payload.get("urls") else "not_applicable",
        encoding="analyzed" if payload.get("encoding") else "not_applicable",
    )

    return {
        "nodes": nodes,
        "edges": edges,
        "correlations": correlations,
        "evidence_ids": evidence_ids,
        "coverage": coverage.to_dict(),
    }


def run_correlation(entities: list[EvidenceEntity], relationships: list[Relationship]) -> list[dict[str, Any]]:
    """Run cross-modal correlation on evidence entities."""
    correlations = []
    entity_map = {e.id: e for e in entities}

    # Extract normalized domain values
    domain_values = []
    url_values = []
    qr_payload = None
    has_qr = any(e.id == "qr" for e in entities)
    for e in entities:
        if e.type in ("Domain", "VisibleDomain"):
            domain_values.append(e.normalizedValue or "")
        if e.type == "URL" and e.source == "url_intelligence":
            url_values.append((e.id, e.normalizedValue or ""))

    # Displayed vs destination mismatch
    for e in entities:
        if e.type == "VisibleDomain" and e.normalizedValue:
            for u in url_values:
                if e.normalizedValue != u[1]:
                    correlations.append({
                        "conflictType": "DISPLAYED_DESTINATION_MISMATCH",
                        "evidenceA": e.id,
                        "evidenceB": u[0],
                        "severity": "high" if e.confidence > 0.8 else "medium",
                        "explanation": "Displayed identity and extracted destination differ.",
                        "entities": [e.id, u[0]],
                    })

    # Also check QR URL vs visible domain - QR destination differs from visible text
    if has_qr:
        qr_entity = entity_map.get("qr")
        if qr_entity and qr_entity.normalizedValue and isinstance(qr_entity.normalizedValue, str):
            qr_payload = qr_entity.normalizedValue
            for e in entities:
                if e.type == "VisibleDomain" and e.normalizedValue:
                    if qr_payload != e.normalizedValue:
                        correlations.append({
                            "conflictType": "QR_VS_VISIBLE_DESTINATION",
                            "evidenceA": "qr",
                            "evidenceB": e.id,
                            "severity": "high",
                            "explanation": "QR destination differs from visible domain text on screen.",
                            "entities": ["qr", e.id],
                        })

    # QR vs URL correlation
    if has_qr:
        qr_entity = entity_map.get("qr")
        if qr_entity and qr_entity.normalizedValue and isinstance(qr_entity.normalizedValue, str):
            qr_payload = qr_entity.normalizedValue
            # Find any URL entities (url_intelligence or ocr)
            url_entities = [e for e in entities if e.type == "URL" and e.normalizedValue and e.id != "qr"]
            for u in url_entities:
                if qr_payload != u.normalizedValue:
                    correlations.append({
                        "conflictType": "QR_VS_URL",
                        "evidenceA": "qr",
                        "evidenceB": u.id,
                        "severity": "high",
                        "explanation": "QR destination differs from extracted URL.",
                        "entities": ["qr", u.id],
                    })

    # C2PA vs detector conflict
    provenance = next((e for e in entities if e.type == "Provenance"), None)
    ensemble = next((e for e in entities if e.type == "DetectorEnsemble"), None)
    if provenance and ensemble:
        if provenance.verified and provenance.polarity == Polarity.SUPPORTS_TRUST:
            correlations.append({
                "conflictType": "C2PA_DETECTOR_CONFLICT",
                "evidenceA": "provenance",
                "evidenceB": "ensemble",
                "severity": "high",
                "explanation": "C2PA assertion conflicts with detector evidence.",
                "entities": ["provenance", "ensemble"],
            })

    return correlations


def build_evidence_entities(payload: dict[str, Any]) -> list[EvidenceEntity]:
    """Build evidence entities from payload."""
    entities: list[EvidenceEntity] = []
    ocr = payload.get("ocr")
    qr = payload.get("qr")
    urls = payload.get("urls") or []
    file_finding = payload.get("file") or {}

    # Input
    entities.append(EvidenceEntity(
        id="input",
        source="input",
        modality=payload.get("mode", "unknown"),
        type="Input",
        title="Input upload",
        rawValue=payload.get("fileName"),
        confidence=1.0,
        verified=True,
        stage="acquisition",
    ))

    # OCR
    if ocr:
        entities.append(EvidenceEntity(
            id="ocr",
            source="ocr",
            modality="ocr",
            type="OCR",
            title="OCR text extracted",
            rawValue=str(ocr.get("text", ""))[:200],
            normalizedValue=ocr.get("normalizedText"),
            confidence=ocr.get("confidence"),
            stage="extraction",
        ))

    # QR
    if qr:
        qr_payload = qr.get("payload")
        qr_norm = qr_payload if qr.get("isUrl") else None
        entities.append(EvidenceEntity(
            id="qr",
            source="qr",
            modality="qr",
            type="QR",
            title="QR code decoded",
            rawValue=qr_payload,
            normalizedValue=qr_norm,
            confidence=0.9 if qr_payload else 0.0,
            stage="extraction",
        ))

    # URLs
    for i, entry in enumerate(urls):
        if entry.get("normalizedCandidate"):
            entities.append(EvidenceEntity(
                id=f"url_{i:03d}",
                source="url_intelligence",
                modality="url_intelligence",
                type="URL",
                title=f"URL: {str(entry.get('normalizedCandidate', ''))[:80]}",
                rawValue=entry.get("rawExtractedText"),
                normalizedValue=entry.get("normalizedCandidate"),
                confidence=entry.get("confidence", 0.7),
                stage="correlation",
            ))

    # File
    if file_finding and file_finding.get("accepted"):
        entities.append(EvidenceEntity(
            id="file",
            source="file_intelligence",
            modality="file_intelligence",
            type="File",
            title=f"File: {str(file_finding.get('fileKind', ''))}",
            rawValue=file_finding.get("sizeBytes"),
            normalizedValue=f"{file_finding.get('textChars')} chars",
            confidence=0.8,
            stage="extraction",
        ))

    # Visible domains from OCR text
    if ocr and isinstance(ocr, dict):
        ocr_text = str(ocr.get("text", ""))
        visible_domains = extract_visible_domains(ocr_text)
        for i, vd in enumerate(visible_domains):
            eid = f"visible_domain_{i:03d}"
            entities.append(EvidenceEntity(
                id=eid,
                source="ocr",
                modality="ocr",
                type="VisibleDomain",
                title=f"Visible domain: {vd.domain}",
                description=f"Raw: {vd.raw}",
                normalizedValue=vd.domain,
                rawValue=vd.raw,
                confidence=vd.confidence,
                stage="extraction",
            ))

    return entities


def build_relationships(entities: list[EvidenceEntity]) -> list[Relationship]:
    """Build relationships from entities."""
    relationships: list[Relationship] = []
    entity_map = {e.id: e for e in entities}

    for i, e in enumerate(entities):
        for j, other in enumerate(entities):
            if i >= j:
                continue
            if e.id == "input":
                relationships.append(Relationship(
                    id=f"rel_{i:03d}",
                    from_entity=e.id,
                    to_entity=other.id,
                    relation="contains",
                    evidence_refs=[e.id, other.id],
                ))
            elif e.type == "OCR" and other.type == "URL":
                if other.normalizedValue:
                    relationships.append(Relationship(
                        id=f"rel_url_{i}_{j}",
                        from_entity=e.id,
                        to_entity=other.id,
                        relation="extracts",
                        evidence_refs=[e.id],
                    ))
            elif e.type == "QR" and other.type == "URL":
                if other.normalizedValue:
                    relationships.append(Relationship(
                        id=f"rel_qr_url_{i}_{j}",
                        from_entity=e.id,
                        to_entity=other.id,
                        relation="decoded_from",
                        evidence_refs=[e.id],
                    ))

    return relationships
