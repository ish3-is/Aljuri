"""
Provenance-first evidence layer (Tier 1 of the BASIRAH architecture).

Design rules, in priority order:

1. MANIFEST PRESENCE IS NOT VERIFICATION. The two are reported as
   separate fields and never collapsed. A file carrying a C2PA manifest
   whose signature does not validate is reported `invalid` /
   `present_unverified`, never `verified`.

2. NO FABRICATED VERIFICATION. If the official SDK is unavailable or
   throws, the result is `unavailable` with the reason attached. We do
   not fall back to "looks like a real manifest, call it verified".

3. ORIGINAL BYTES ONLY. Verification runs against the bytes exactly as
   uploaded, BEFORE any resize, re-encode or normalisation. Verifying a
   rewritten copy would destroy the very manifest being checked.

4. A VERIFIED MANIFEST IS NOT PROOF OF AUTHENTICITY. A valid C2PA
   manifest may assert generative creation, ordinary editing, or camera
   capture. The assertions decide what may be claimed, so they are
   parsed and surfaced rather than summarised as "verified".

5. NOTHING IS FETCHED. Ingredient references and any URL inside a
   manifest are treated as inert strings. This module performs no
   network I/O of any kind.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProvenanceStatus(str, Enum):
    VERIFIED = "verified"
    PRESENT_UNVERIFIED = "present_unverified"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"


class EvidenceStrength(str, Enum):
    """Tier 4 strength model. See Section 4 of the brief."""

    VERY_HIGH = "very_high"   # cryptographically verified assertion
    HIGH = "high"             # multiple independent validated signals
    MEDIUM = "medium"         # strong agreement between independent detectors
    LOW = "low"               # one detector, weak metadata, isolated indicator
    NEUTRAL = "neutral"       # absence of a signal is not a finding


# Manifest assertion/action strings that legitimately indicate
# generative or AI-assisted creation. Matched case-insensitively against
# the RAW assertion text so the original wording is preserved, and never
# inferred from an unfamiliar action name.
#
# Ordering matters. `c2pa.created` is the C2PA action for authoring new
# content and is generative when its software agent is a generator;
# `c2pa.edited` is only an ordinary edit on its own. An AI-edit verdict
# therefore comes from the agent attached to the action, not from the
# action name, which is why `ai_edited` is decided separately below.
_GENERATIVE_TOKENS = (
    "c2pa.created",
    "c2pa.generated",
    "ai_generated",
    "aigenerated",
    "generative_ai",
    "generativeai",
    "created with ai",
    "digital.ai",
    "trainedalgorithmicmedia",
)
_EDIT_TOKENS = ("c2pa.edited", "edited", "composited", "converted", "transcoded")
_CAPTURE_TOKENS = ("c2pa.captured", "capture", "photograph")

# An edit is attributed to AI when its software agent says so.
_AI_AGENT_TOKENS = (
    "ai", "gpt", "dall", "midjourney", "stable", "diffusion", "firefly",
    "flux", "gemini", "imagen", "sdxl", "leonardo", "generative",
)


@dataclass
class ProvenanceResult:
    status: ProvenanceStatus
    standard: str | None = None
    manifest_present: bool = False
    signature_verified: bool | None = None
    signer: str | None = None
    issuer: str | None = None
    generator_or_tool: str | None = None
    ai_generated_assertion: bool | None = None
    ai_edited_assertion: bool | None = None
    capture_assertion: bool | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    raw_claims_available: bool = False
    sdk_available: bool = False
    evidence_strength: EvidenceStrength = EvidenceStrength.NEUTRAL
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialised form. Deliberately omits any filesystem path, temp
        filename or certificate material.
        """
        return {
            "status": self.status.value,
            "standard": self.standard,
            "manifestPresent": self.manifest_present,
            "signatureVerified": self.signature_verified,
            "signer": self.signer,
            "issuer": self.issuer,
            "generatorOrTool": self.generator_or_tool,
            "aiGeneratedAssertion": self.ai_generated_assertion,
            "aiEditedAssertion": self.ai_edited_assertion,
            "captureAssertion": self.capture_assertion,
            "actions": self.actions,
            "ingredients": self.ingredients,
            "validationErrors": self.validation_errors,
            "validationWarnings": self.validation_warnings,
            "rawClaimsAvailable": self.raw_claims_available,
            "sdkAvailable": self.sdk_available,
            "evidenceStrength": self.evidence_strength.value,
            "notes": self.notes,
        }


def _classify(raw: str) -> str:
    low = raw.lower()
    if any(tok in low for tok in _GENERATIVE_TOKENS):
        return "generative"
    if any(tok in low for tok in _CAPTURE_TOKENS):
        return "capture"
    if any(tok in low for tok in _EDIT_TOKENS):
        return "edit"
    return "other"


def _safe_string(value: Any, limit: int = 240) -> str | None:
    """Manifest fields are attacker-controlled; bound their size."""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v:
        return None
    return v[:limit]


def _manifest_bytes(data: bytes) -> bool:
    """
    Cheap pre-check for a C2PA/JUMBF box.

    Only used to report manifest PRESENCE. It never implies validity,
    and an attacker can trivially embed the magic bytes, which is
    exactly why presence and verification are separate fields.
    """
    for marker in (b"c2pa", b"jumb", b"c2pa."):
        if marker in data[:200_000] or marker in data[-200_000:]:
            return True
    return False


def _sdk_importable() -> bool:
    """Report SDK availability honestly, even when no manifest was found."""
    try:
        import c2pa  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _detect_mime(data: bytes) -> str:
    """
    Sniff the container so the correct C2PA reader path is used.

    Detection is on magic bytes, not on the client-supplied filename or
    Content-Type, both of which are attacker-controlled.
    """
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:5] == b"{\\rtf":
        return "application/rtf"
    if data[:4] == b"%PDF":
        return "application/pdf"
    return "image/jpeg"


def verify_provenance(data: bytes) -> ProvenanceResult:
    """
    Verify Content Credentials on ORIGINAL uploaded bytes.

    Never raises: an unavailable SDK or a malformed manifest is
    reported honestly rather than crashing the analysis pipeline.
    """
    if not _manifest_bytes(data):
        # Absence is NEUTRAL. Not a finding, not suspicious, not proof.
        return ProvenanceResult(
            status=ProvenanceStatus.UNAVAILABLE,
            sdk_available=_sdk_importable(),
            notes=[
                "No Content Credentials manifest was found.",
                "Absence of credentials does not indicate authenticity "
                "or manipulation; it only means no claim was published.",
            ],
        )

    try:
        from c2pa import Reader as C2paReader  # type: ignore
        from c2pa import C2paError  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return ProvenanceResult(
            status=ProvenanceStatus.PRESENT_UNVERIFIED,
            manifest_present=True,
            signature_verified=False,
            sdk_available=False,
            validation_errors=[f"C2PA SDK unavailable: {type(exc).__name__}"],
            notes=[
                "A manifest appears to be embedded but could not be "
                "cryptographically verified because the C2PA SDK is "
                "not available. Treated as unverified, not as valid.",
            ],
        )

    mime = _detect_mime(data)
    result = ProvenanceResult(
        status=ProvenanceStatus.UNAVAILABLE,
        manifest_present=True,
        sdk_available=True,
        standard="C2PA",
    )

    try:
        # NOTE: verified against ORIGINAL bytes. Any resize or re-encode
        # performed for detector inference would destroy the manifest.
        reader = C2paReader(mime, io.BytesIO(data))
        validation = reader.get_validation_results() or {}
        manifest_json = reader.json()
        result.raw_claims_available = True
    except C2paError as exc:
        msg = _safe_string(str(exc), 300) or "C2PA validation failed"
        low = msg.lower()
        if "notfound" in low or "no jumbf" in low or "no manifest" in low:
            # The SDK found nothing. Whatever magic bytes triggered our
            # pre-check are not a real manifest.
            result.status = ProvenanceStatus.UNAVAILABLE
            result.manifest_present = False
            result.notes.append(
                "No verifiable Content Credentials were found. The "
                "absence of credentials does not prove that this content "
                "is authentic or synthetic."
            )
        elif "invalid" in low or "malformed" in low or "corrupt" in low:
            result.status = ProvenanceStatus.INVALID
            result.signature_verified = False
            result.evidence_strength = EvidenceStrength.LOW
            result.validation_errors.append(msg)
            result.notes.append(
                "Embedded provenance information is present but failed "
                "validation. It is not treated as trustworthy."
            )
        else:
            result.status = ProvenanceStatus.PRESENT_UNVERIFIED
            result.signature_verified = False
            result.validation_errors.append(msg)
        return result
    except Exception as exc:  # noqa: BLE001
        result.status = ProvenanceStatus.PRESENT_UNVERIFIED
        result.signature_verified = False
        result.validation_errors.append(f"{type(exc).__name__}: {_safe_string(str(exc))}")
        return result

    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(manifest_json)
    except Exception:  # noqa: BLE001
        result.validation_warnings.append("Manifest JSON could not be parsed.")

    # ---- validation outcome -------------------------------------------
    signature_ok = _sdk_flag(validation, ("signature",))
    claim_ok = _sdk_flag(validation, ("claim",))
    # Fall back to the SDK's own top-level verdicts when the structured
    # results are absent.
    if signature_ok is None:
        signature_ok = bool(validation.get("signature_valid")) if validation else None

    result.signature_verified = signature_ok

    if signature_ok is True:
        result.status = ProvenanceStatus.VERIFIED
        result.evidence_strength = EvidenceStrength.VERY_HIGH
    elif signature_ok is False:
        result.status = ProvenanceStatus.INVALID
        result.evidence_strength = EvidenceStrength.LOW
        result.validation_errors.append("Manifest signature did not validate.")
        result.notes.append(
            "A Content Credentials manifest is present but its signature "
            "did not validate. It is reported as invalid, not as evidence."
        )
    else:
        result.status = ProvenanceStatus.PRESENT_UNVERIFIED
        result.evidence_strength = EvidenceStrength.LOW
        result.validation_warnings.append(
            "Manifest parsed but signature state could not be confirmed."
        )

    if claim_ok is False and signature_ok is True:
        result.validation_warnings.append(
            "Manifest signature validated but a claim did not."
        )

    for bucket, attr in (("validation_errors", "validation_errors"),
                         ("validation_warnings", "validation_warnings")):
        for err in (parsed.get(bucket) or [])[:20]:
            safe = _safe_string(str(err), 300)
            if safe:
                getattr(result, attr).append(safe)

    # ---- signer / issuer ----------------------------------------------
    # The SDK can return active_manifest as a str in edge cases (for
    # example a raw C2PA packet). Guard so a non-dict never reaches .get()
    # and raises AttributeError up the stack.
    active = parsed.get("active_manifest")
    if not isinstance(active, dict):
        active = {}
    sig = active.get("signature_info") or {}
    if isinstance(sig, dict):
        result.signer = _safe_string(
            sig.get("signer") or sig.get("common_name") or sig.get("organization")
        )
        chain = sig.get("certificate_chain") or sig.get("chain")
        if isinstance(chain, list) and chain:
            first = chain[0]
            if isinstance(first, dict):
                result.issuer = _safe_string(first.get("subject") or first.get("issuer"))

    # ---- assertions / actions -----------------------------------------
    generative = False
    edited = False
    ai_edited = False
    capture = False
    actions = active.get("actions") or []
    for act in actions:
        if not isinstance(act, dict):
            continue
        raw_action = _safe_string(act.get("action"), 200)
        agent = _safe_string(str(act.get("softwareAgent") or ""), 200)
        kind = _classify(raw_action or "")
        if kind == "generative":
            generative = True
        elif kind == "edit":
            edited = True
            # An edit is AI-attributed from its agent, never from the
            # generic action name alone.
            if agent and any(tok in agent.lower() for tok in _AI_AGENT_TOKENS):
                ai_edited = True
        elif kind == "capture":
            capture = True
        result.actions.append({
            "action": raw_action,
            "kind": kind,
            "when": _safe_string(act.get("when"), 60),
            "softwareAgent": agent,
        })
        if agent and not result.generator_or_tool:
            result.generator_or_tool = agent

    # Tri-state, and deliberately never False:
    #   True  -> the manifest positively asserts AI involvement
    #   None  -> the manifest makes no such assertion
    # A plain capture or a Photoshop edit asserts nothing about AI, so
    # reporting False would mean "the manifest states this is not AI",
    # which it never said. We do not manufacture a negative we cannot
    # verify.
    ai_involved = generative or ai_edited
    result.ai_generated_assertion = True if ai_involved else None
    result.ai_edited_assertion = True if ai_edited else None
    result.capture_assertion = True if capture else None

    # ---- ingredients ---------------------------------------------------
    for ing in (active.get("ingredients") or [])[:20]:
        if not isinstance(ing, dict):
            continue
        # URLs are recorded as inert evidence strings. Nothing is fetched.
        result.ingredients.append({
            "title": _safe_string(ing.get("title"), 160),
            "instanceId": _safe_string(ing.get("instanceId"), 160),
            "relationship": _safe_string(ing.get("relationship"), 40),
        })

    if result.status is ProvenanceStatus.VERIFIED and ai_involved:
        result.notes.append(
            "Verified credentials assert generative creation. This "
            "outranks pixel-detector disagreement."
        )
    elif result.status is ProvenanceStatus.VERIFIED:
        result.notes.append(
            "Credentials are valid but do not make an AI-generation "
            "assertion. A valid manifest alone does not establish that "
            "the content is camera-authentic."
        )

    return result


def _sdk_flag(validation: dict[str, Any], keys: tuple[str, ...]) -> bool | None:
    """
    Read a tri-state flag out of the SDK's validation results.

    Returns None when the SDK did not report on this aspect, which is
    materially different from reporting failure.
    """
    if not isinstance(validation, dict):
        return None
    results = validation.get("validation_results")
    if isinstance(results, list):
        for entry in results:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("validation_status") or entry.get("label") or "").lower()
            if not any(k in label for k in keys):
                continue
            ok = entry.get("success")
            if ok is None:
                ok = entry.get("valid")
            if ok is not None:
                return bool(ok)
    for key in keys:
        for probe in (f"{key}_valid", f"{key}_validated", f"is_{key}_valid"):
            if probe in validation:
                return bool(validation[probe])
    return None
