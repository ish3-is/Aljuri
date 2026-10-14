"""
POST /api/analyze/evidence — the multimodal orchestrator.

Runs the full evidence chain for one upload and returns a single
normalised response:

    validation -> provenance -> image ensemble -> OCR -> QR
                -> URL extraction -> URL intelligence -> encoding
                -> metadata -> forensics -> fusion

Fusion is deterministic and explainable. Probabilities from different
modalities are NEVER averaged: a QR code pointing at a high-risk URL is
categorically different evidence from a pixel detector's opinion, and
collapsing them into one number destroys exactly the information a
committee needs.

Nothing is fetched. URLs are scored as strings by the local engine.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from app.content_intel import decode_qr, inspect_encoded, recover_urls, run_ocr
from app.evidence.correlation import build_evidence_entities, build_relationships
from app.file_intel import inspect_file
from app.image.ensemble.policy import (
    Agreement,
    Assessment,
    Distribution,
    EvidenceQuality,
)

MAX_STAGE_SECONDS = 30.0


def _stage(name: str, events: list[dict[str, Any]], status: str = "ok",
           detail: str = "") -> None:
    events.append({"stage": name, "status": status, "detail": detail})


def _time_it(fn, *args, **kwargs):
    started = time.perf_counter()
    try:
        value = fn(*args, **kwargs)
        return value, round((time.perf_counter() - started) * 1000, 2), None
    except Exception as exc:  # noqa: BLE001
        return None, round((time.perf_counter() - started) * 1000, 2), \
            f"{type(exc).__name__}: {exc}"


def analyze_evidence(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    mode: str = "auto",
) -> dict[str, Any]:
    """
    Analyse one uploaded artefact across every applicable modality.

    `mode` selects the pipeline: "auto" infers from the actual bytes,
    and an explicit mode that contradicts the content is reported rather
    than silently obeyed.
    """
    started = time.perf_counter()
    events: list[dict[str, Any]] = []
    latencies: dict[str, float] = {}

    name = filename or "upload"
    resolved = _resolve_mode(data, name, mode)
    conflict = _mode_conflict(data, name, mode)
    _stage("mode_resolved", events,
           status="warning" if conflict else "ok",
           detail=resolved if not conflict else f"{resolved} (conflict)")

    response: dict[str, Any] = {
        "analysisType": "evidence",
        "mode": resolved,
        "requestedMode": mode,
        "fileName": name,
        "fileSizeBytes": len(data),
        "limitations": [],
    }
    if conflict:
        response["modeConflict"] = conflict
        response["limitations"].append(conflict)

    # ---- image path -----------------------------------------------------
    if resolved in ("image", "screenshot"):
        from app.image.service import analyze_image
        result, ms, err = _time_it(analyze_image, data,
                                   original_name=name, content_type=content_type)
        latencies["image_analysis"] = ms
        if err:
            _stage("image_analysis", events, "error", err)
            response["image"] = {"available": False, "reason": err}
        else:
            _stage("image_analysis", events, detail=f"{ms} ms")
            response["image"] = result
            response["trustAssessment"] = result.get("trustAssessment")
            response["finalAssessment"] = result.get("finalAssessment")
            response["provenance"] = result.get("provenance")
            response["ensemble"] = result.get("ensemble")
            response["metadata"] = result.get("metadata")
            response["forensics"] = result.get("forensics")
            response["evidenceQuality"] = result.get("evidenceQuality")

    # ---- OCR ------------------------------------------------------------
    if resolved in ("image", "screenshot", "file"):
        ocr, ms, err = _time_it(run_ocr, data)
        latencies["ocr"] = ms
        if err:
            _stage("ocr", events, "error", err)
            response["ocr"] = {"available": False, "reason": err}
        else:
            _stage("ocr", events, detail=f"{ms} ms via {ocr.engine}")
            response["ocr"] = ocr.to_dict()

    # ---- QR -------------------------------------------------------------
    if resolved in ("image", "screenshot"):
        qr, ms, err = _time_it(decode_qr, data)
        latencies["qr"] = ms
        if err:
            _stage("qr", events, "error", err)
            response["qr"] = {"available": False, "reason": err}
        else:
            _stage("qr", events, detail=f"{qr.decode_status} on attempt {qr.attempt_used}")
            response["qr"] = qr.to_dict()

    # ---- URL extraction + URL intelligence ------------------------------
    candidates: list[dict[str, Any]] = []
    if response.get("qr", {}).get("payload") and response["qr"].get("isUrl"):
        candidates.append({
            "rawExtractedText": response["qr"]["payload"],
            "normalizedCandidate": response["qr"]["payload"],
            "repairApplied": False,
            "repairNotes": ["decoded from QR symbol"],
            "confidence": 1.0,
            "origin": "qr",
        })
    for c in (response.get("ocr", {}).get("urls") or []):
        # `response["ocr"]` is already the serialised dict, so these are
        # plain dicts, not UrlCandidate instances.
        entry = dict(c) if isinstance(c, dict) else c.to_dict()
        candidates.append({**entry, "origin": "ocr"})

    # ---- file intelligence ----------------------------------------------
    if resolved == "file":
        fin, ms, err = _time_it(inspect_file, data, name)
        latencies["file_inspection"] = ms
        if err:
            _stage("file_inspection", events, "error", err)
            response["file"] = {"available": False, "reason": err}
        else:
            _stage("file_inspection", events, detail=f"{ms} ms")
            response["file"] = fin.to_dict()
            if fin.accepted:
                enc, ms2, _ = _time_it(inspect_encoded, _safe_text(data))
                latencies["encoding"] = ms2
                response["encoding"] = [e.to_dict() for e in enc]
            # URLs inside a text file must go through the same recovery
            # and scoring path as OCR text, otherwise a phishing .txt
            # upload reports no URLs at all.
            for u in recover_urls(_safe_text(data)):
                entry = u.to_dict()
                scored, ms3, err3 = _time_it(_score_url, entry["normalizedCandidate"])
                latencies[f"url_intelligence_{len(entry and [u])}"] = ms3
                entry["urlIntelligence"] = scored if not err3 else {
                    "available": False, "reason": err3}
                entry["origin"] = "file_text"
                candidates.append(entry)

    url_findings: list[dict[str, Any]] = []
    for cand in candidates:
        scored, ms, err = _time_it(_score_url, cand["normalizedCandidate"])
        latencies[f"url_intelligence_{len(url_findings)}"] = ms
        entry = {**cand}
        if err:
            entry["urlIntelligence"] = {"available": False, "reason": err}
        else:
            entry["urlIntelligence"] = scored
        url_findings.append(entry)
    if url_findings:
        _stage("url_intelligence", events, detail=f"{len(url_findings)} candidate(s)")
    response["urls"] = url_findings

    # ---- fusion ---------------------------------------------------------
    fusion = fuse(response)
    _stage("evidence_fusion", events, detail=fusion["finalAssessment"])
    response["fusion"] = fusion
    response["timeline"] = events
    response["latencyMs"] = {**latencies,
                             "total": round((time.perf_counter() - started) * 1000, 2)}
    response["limitations"] = fusion["limitations"]
    response["fingerprint"] = hashlib.sha256(data).hexdigest()
    response["coverage"] = compute_coverage(events)
    response["reportTraceability"] = [f"F-{i+1:03d}" for i in range(len(fusion["findings"]))]
    return response


def _safe_text(data: bytes) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _score_url(url: str) -> dict[str, Any]:
    """
    Score a URL with the existing engine. The URL is treated as a STRING
    and is never fetched, resolved or opened.
    """
    from app.services.analyzer import URLAnalysisError, analyze_url

    try:
        result = analyze_url(url)
    except URLAnalysisError as exc:
        return {
            "available": False,
            "reason": exc.payload.code,
            "note": "URL rejected by the URL engine; it was not fetched.",
        }
    # analyze_url returns a Pydantic model, not a dict. Calling .get()
    # on it returned None for every field, which surfaced as
    # "risk=None" rather than as an error -- a silent wrong answer.
    data = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    return {
        "available": True,
        "trustScore": data.get("trustScore"),
        "riskLevel": data.get("riskLevel"),
        "confidence": data.get("confidence"),
        "modelStatus": data.get("source"),
        "note": "URL scored as a string by the local URL engine. "
                "It was not fetched, resolved or opened.",
    }


def _resolve_mode(data: bytes, filename: str, requested: str) -> str:
    """
    Infer the pipeline from the actual bytes, not the extension.

    `classify()` distinguishes a text file by its PARSER ("text"), but
    the evidence pipeline branches on the DELIVERY mode ("file"), so the
    two vocabularies are reconciled here. Getting this wrong meant every
    text file silently skipped file inspection.

    Returns a clean mode token ONLY. A conflict between the requested
    mode and the actual bytes used to be appended to this string, which
    broke every downstream `resolved in ("image", "screenshot")` test
    and silently reduced a full analysis to a stub with no image,
    provenance, OCR or QR. The conflict is reported separately.
    """
    from app.file_intel import classify

    is_image = (data[:3] == b"\xff\xd8\xff"
                or data[:8] == b"\x89PNG\r\n\x1a\n"
                or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"))
    if is_image:
        return "image"
    return {"text": "file", "pdf": "file"}.get(classify(filename), "file")


def _mode_conflict(data: bytes, filename: str, requested: str) -> str | None:
    """Explain a requested/inferred mismatch without corrupting the mode."""
    if requested == "auto":
        return None
    if _resolve_mode(data, filename, requested) == requested:
        return None
    return (
        f"Requested mode '{requested}' was overridden to "
        f"'{_resolve_mode(data, filename, requested)}' because the actual "
        "file content determines the applicable pipeline. The bytes are "
        "the authority, not the extension or the requested mode."
    )


def compute_coverage(events: list[dict[str, Any]]) -> dict[str, str]:
    """Compute coverage from analysis events."""
    coverage = {
        'imagePixels': 0,
        'provenance': 'not_applicable',
        'ocr': 'not_applicable',
        'qr': 'not_applicable',
        'url': 'not_applicable',
        'encoding': 'not_applicable',
        'fileStructure': 'n/a',
    }
    for ev in events:
        if ev.get('stage') == 'provenance' and ev.get('status') == 'ok':
            coverage['provenance'] = 'available'
        elif ev.get('stage') == 'ocr' and ev.get('status') == 'ok':
            coverage['ocr'] = 'analyzed'
        elif ev.get('stage') == 'qr' and ev.get('status') == 'ok':
            coverage['qr'] = 'analyzed'
        elif ev.get('stage') == 'url_intelligence' and ev.get('status') == 'ok':
            coverage['url'] = 'analyzed'
        elif ev.get('stage') == 'encoding' and ev.get('status') == 'ok':
            coverage['encoding'] = 'analyzed'
    return coverage

def fuse(response: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic evidence fusion.

    Tiers, strongest first:
      1 cryptographically verified provenance assertion
      2 strong independent cross-modal evidence (e.g. QR -> high-risk URL)
      3 detector ensemble agreement
      4 metadata / forensic indicators
      5 weak heuristic signals

    Probabilities are never averaged across modalities.
    """
    limitations: list[str] = []
    findings: list[dict[str, Any]] = []

    prov = response.get("provenance") or {}
    prov_status = prov.get("status")
    ai_asserted = prov.get("aiGeneratedAssertion") is True

    if prov_status == "verified" and ai_asserted:
        findings.append({
            "tier": 1, "source": "provenance", "strength": "very_high",
            "claim": "Verified credentials assert generative creation.",
            "polarity": "synthetic",
        })
        final = Assessment.PROVENANCE_VERIFIED
    else:
        final = None

    # Tier 2: a high-risk destination is categorical evidence, not a
    # detector opinion. It applies whether the URL came from a QR symbol,
    # from OCR text on screen, or from an uploaded text file -- in all
    # three cases a human is being pointed somewhere dangerous.
    qr_risk = None
    for entry in response.get("urls") or []:
        ui = entry.get("urlIntelligence") or {}
        if ui.get("riskLevel") != "high_risk":
            continue
        qr_risk = "high_risk"
        findings.append({
            "tier": 2,
            "source": f"url_{entry.get('origin', 'unknown')}",
            "strength": "high",
            "claim": (
                f"A destination visible in this content scored high risk "
                f"by URL Intelligence ({entry.get('normalizedCandidate', '')[:60]})."
            ),
            "polarity": "risky",
        })

    # Tier 3: detector ensemble.
    ens = response.get("ensemble") or {}
    if ens.get("detectorAgreement") == Agreement.STRONG.value:
        findings.append({
            "tier": 3, "source": "detector_ensemble", "strength": "medium",
            "claim": "Both detectors agree strongly.",
            "polarity": "synthetic" if ens.get("syntheticLikelihood", 0) >= 0.5 else "no_indicators",
        })

    assessment = final
    if assessment is None:
        if ens.get("abstained") and not qr_risk:
            assessment = Assessment.UNCERTAIN
            limitations.append(
                "The detectors abstained: "
                + ", ".join(ens.get("abstentionReasons") or ["insufficient evidence"])
            )
        elif ens.get("finalAssessment") and not qr_risk:
            assessment = Assessment(ens["finalAssessment"])
        elif qr_risk == "high_risk":
            # A high-risk destination is actionable even when the pixels
            # look fine or the detectors abstained. Abstention means "no
            # image evidence", not "no evidence": collapsing this to
            # UNCERTAIN would throw away the strongest signal present.
            assessment = Assessment.LIKELY_SYNTHETIC
            limitations.append(
                "Assessment is driven by a high-risk destination visible in "
                "the content, not by the image detectors, which "
                + ("abstained." if ens.get("abstained") else "found no strong indicators.")
            )
        else:
            assessment = Assessment.UNCERTAIN

    if ens.get("distributionStatus") == Distribution.OUT.value:
        limitations.append(
            "The image resembles none of the validated distributions, so "
            "detector evidence carries less weight."
        )
    if prov_status == "unavailable":
        limitations.append(
            "No Content Credentials were found. Their absence is neutral: "
            "it is not evidence that the content is authentic or synthetic."
        )
    if response.get("mode", "").startswith("file") and \
            (response.get("file") or {}).get("accepted") is False:
        limitations.append((response.get("file") or {}).get("reason") or
                            "file not inspected")

    return {
        "finalAssessment": assessment.value,
        "findings": findings,
        "evidenceHierarchy": [
            "verified provenance",
            "strong cross-modal evidence",
            "detector agreement",
            "metadata / forensics",
            "weak heuristics",
        ],
        "limitations": limitations,
        "note": (
            "Modalities are not averaged. A verified provenance assertion "
            "outranks pixel detectors, and a QR destination scoring high "
            "risk is not diluted by an image that merely looks real."
        ),
    }
