"""
Content intelligence: OCR routing, QR decoding, URL recovery and
safe encoded-content inspection.

Three rules govern everything here.

1. NOTHING DECODED IS EVER EXECUTED. Base64/Hex/JWT payloads are
   decoded into inert text for inspection only. There is no eval, no
   deserialisation of the decoded object, and no import.

2. NOTHING IS FETCHED. A URL found in a QR code or in OCR output is a
   string. It is scored by the local URL engine and never opened.

3. REPAIR IS CONSERVATIVE AND AUDITED. OCR routinely destroys URL
   punctuation (`https: /secure bank-verify example login`). Repairing
   that is genuinely useful for phishing analysis, but inventing a
   domain is not. Every repaired candidate keeps its raw text and a
   record of exactly what was changed, so a reviewer can reject it.
"""

from __future__ import annotations

import base64
import binascii
import io
import os
import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TESSERACT_BIN = os.environ.get(
    "TESSERACT_BIN",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

# This module lives at backend/app/content_intel.py, so parents[1] is the
# backend root. Using parents[2] pointed at the project root one level
# higher, where tools/tessdata does not exist -- and because Tesseract
# was then handed a non-existent --tessdata-dir it returned empty
# output on every image while the function still reported success.
_TESSDATA = Path(__file__).resolve().parents[1] / "tools" / "tessdata"

MAX_DECODE_DEPTH = 3
MAX_DECODED_BYTES = 64 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024

_ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿ]")
_OCR_ENGINE: dict[str, Any] = {}


# --------------------------------------------------------------------------
# URL recovery
# --------------------------------------------------------------------------

# Deliberately narrow. A "repaired" URL must be traceable to characters
# that were actually present in the OCR output.
_SCHEME_SPLIT = re.compile(r"^(https?)\s*[:：]?\s*[/／\\]{1,2}\s*", re.I)
_HOST_GAP = re.compile(r"(?<=[a-z0-9])\s*[.．]\s*(?=[a-z0-9])", re.I)
_SCHEME_GAP = re.compile(r"^(https?)\s+(?=//|www\.)", re.I)
_DOT_WORD = re.compile(r"\b(https?)\s+(?=www\.)", re.I)
_HOSTISH = re.compile(r"(?:https?:|www\.)[^\s<>\"']{3,}", re.I)


@dataclass
class UrlCandidate:
    raw_text: str
    candidate: str
    repair_applied: bool
    repair_notes: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rawExtractedText": self.raw_text,
            "normalizedCandidate": self.candidate,
            "repairApplied": self.repair_applied,
            "repairNotes": list(self.repair_notes),
            "confidence": round(self.confidence, 3),
        }


def _looks_like_host(text: str) -> bool:
    """
    Is there a plausible registrable host in this candidate?

    The scheme must be stripped FIRST: splitting 'https://a.example/p'
    on '/' yields 'https:', and splitting that on ':' yields 'https',
    which has no dot and would reject every real URL.
    """
    body = re.sub(r"^[a-z][a-z0-9+.\-]*:\/\/", "", text, flags=re.I)
    host = body.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    # strip credentials and port
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    if not host or "." not in host:
        return False
    tld = host.rsplit(".", 1)[-1].lower()
    if not (2 <= len(tld) <= 24 and tld.isalpha()):
        return False
    return all(part and len(part) <= 63 for part in host.split("."))


# Words that are never part of a URL. Without this, "https://a.example/path now"
# absorbs "now" because it is lower-case and URL-shaped.
_URL_STOPWORDS = {
    "now", "today", "please", "click", "here", "this", "that", "the", "and",
    "for", "your", "you", "our", "with", "from", "into", "open", "visit",
    "go", "to", "at", "in", "on", "is", "it", "a", "an", "of", "or", "as",
    "if", "be", "by", "we", "us", "can", "will", "has", "have", "was",
}

# Tokens after the scheme that may be host labels or path segments.
_URL_TOKEN = re.compile(r"^[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+$")


def _consume_url_tokens(tokens: list[str], start: int) -> tuple[str, int]:
    """
    Walk forward from a URL-looking token, absorbing the pieces that OCR
    split apart.

    OCR emits "https: /secure bank-verify example login" as separate
    whitespace-delimited tokens. A regex alone can never join them,
    because the separators it would need to match are exactly the
    whitespace that split them. So continuation is decided per token:
    keep taking while the token can plausibly belong to a host or path,
    and stop as soon as it clearly does not.
    """
    parts = [tokens[start]]
    i = start + 1
    while i < len(tokens):
        tok = tokens[i]
        bare = tok.strip(".,;:!?()[]{}\"'").lower()
        if not bare:
            break
        # Trailing prose must not be swallowed as part of the URL.
        if bare in _URL_STOPWORDS and parts:
            break
        if _URL_TOKEN.match(tok.strip(".,;:!?()[]{}\"'")):
            parts.append(tok.strip(".,;:!?()[]{}\"'"))
            i += 1
            continue
        break
    return " ".join(parts), i


def recover_urls(text: str) -> list[UrlCandidate]:
    """
    Recover URL-shaped strings from noisy OCR output.

    Conservative by design: punctuation is restored only when the
    surrounding characters already form a plausible host, so ordinary
    prose containing " . " is not promoted into a URL.
    """
    out: list[UrlCandidate] = []
    # Ambiguous shapes are collected separately and returned with empty
    # candidates, so a caller cannot accidentally score a guess.
    unresolved: list[UrlCandidate] = []
    seen: set[str] = set()

    tokens = text.split()
    i = 0
    while i < len(tokens):
        # A bare "www" token is also a start: OCR frequently splits
        # "www.example.com" into "www", ".", "example", ".", "com", so
        # requiring a literal "www." missed the shape entirely.
        if not re.match(r"^(https?:|hxxps|www\.|http\s)", tokens[i], re.I) \
                and not (tokens[i].lower() == "www" and i + 1 < len(tokens)
                         and tokens[i + 1].strip() in (".", "．")):
            i += 1
            continue

        joined, nxt = _consume_url_tokens(tokens, i)
        raw = joined
        notes: list[str] = []
        candidate = joined

        # Defated/obfuscated scheme: "hxxps[:]//", "hxxps://", "hxxps//".
        # Written as explicit alternatives because a character class here
        # silently consumed only the "[" and left ":]" behind, producing
        # the malformed "https:]//host".
        deflated = re.sub(
            r"^h(?:xx|XX)(?:ps|PS)\s*(?:\[\s*:?\s*\]|[:：])?\s*(?=[/／\\]|$)",
            "https", candidate, flags=re.I,
        )
        if deflated != candidate:
            notes.append("expanded deflated scheme 'hxxps'")
            candidate = deflated
        bracket = re.sub(r"^(https?)\s+", r"\1", candidate, flags=re.I)
        if bracket != candidate:
            notes.append("removed space after scheme")
            candidate = bracket
        # https: /host  ->  https://host
        sep = re.sub(r"^(https?):\s*[/／\\]{1,2}\s*", r"\1://", candidate, flags=re.I)
        if sep != candidate:
            notes.append("repaired split scheme separator")
            candidate = sep
        else:
            # OCR frequently drops the colon: "https//host".
            nocolon = re.sub(r"^(https?)[/／\\]{1,2}", r"\1://", candidate, flags=re.I)
            if nocolon != candidate:
                notes.append("restored missing scheme colon")
                candidate = nocolon
        if re.match(r"^https?://?$", candidate, re.I):
            i = nxt
            continue

        # [.] / [dot] and whitespace around dots
        bracket_dots = re.sub(r"\[\s*\.\s*\]|\[\s*dot\s*\]", ".", candidate, flags=re.I)
        if bracket_dots != candidate:
            notes.append("unbracketed host separator '[.]'")
            candidate = bracket_dots
        spaced = _HOST_GAP.sub(".", candidate)
        if spaced != candidate:
            notes.append("removed whitespace around host separators")
            candidate = spaced

        # OCR sometimes replaces host separators with spaces entirely
        # ("secure bank-verify example login"). The original separators
        # are then UNRECOVERABLE: "-" and "." are indistinguishable once
        # the punctuation is gone, and guessing one of them would
        # fabricate a domain that a user could act on. The measurement
        # showed exactly that risk, so an ambiguous shape is reported as
        # unresolved instead of being repaired.
        if not _looks_like_host(candidate):
                    # Partition on the BODY, not the raw string: splitting
                    # "https://a b c" on "/" yields head="https:" because the
                    # scheme's own slashes come first, which made the token list
                    # one element long and the rule never fire.
                    body = re.sub(r"^[a-z][a-z0-9+.\-]*:\/\/", "", candidate, flags=re.I)
                    head, sep, tail = body.partition("/")
                    tokens = [t for t in head.split() if t]
                    if len(tokens) >= 2 and re.fullmatch(r"[A-Za-z]{2,24}", tokens[-1]):
                        unresolved.append(UrlCandidate(
                            raw_text=raw,
                            candidate="",
                            repair_applied=False,
                            repair_notes=[
                                "candidate_unresolved: OCR destroyed the host "
                                "separators, so the domain cannot be reconstructed "
                                "without guessing. Reported rather than invented."
                            ],
                            confidence=0.0,
                        ))

        # www.example.com -> https://www.example.com
        if re.match(r"^www\.", candidate, re.I):
            candidate = "https://" + candidate
            notes.append("added scheme to bare 'www.' host")

        candidate = candidate.rstrip(".,;:!?)]}'\"")
        if _looks_like_host(candidate) and candidate.lower() not in seen:
            seen.add(candidate.lower())
            out.append(UrlCandidate(
                raw_text=raw,
                candidate=candidate,
                repair_applied=bool(notes),
                repair_notes=notes,
                confidence=0.75 if notes else 0.95,
            ))
        i = max(nxt, i + 1)
    return out + unresolved


# --------------------------------------------------------------------------
# OCR router
# --------------------------------------------------------------------------

@dataclass
class OcrResult:
    engine: str
    text: str
    normalized_text: str
    confidence: float | None
    has_arabic: bool
    lines: list[dict[str, Any]] = field(default_factory=list)
    urls: list[UrlCandidate] = field(default_factory=list)
    engines_used: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "enginesUsed": self.engines_used,
            "text": self.text,
            "normalizedText": self.normalized_text,
            "confidence": None if self.confidence is None else round(self.confidence, 3),
            "containsArabic": self.has_arabic,
            "lines": self.lines,
            "urls": [u.to_dict() for u in self.urls],
            "notes": self.notes,
        }


def _normalize(text: str) -> str:
    """Fold bidi control characters and presentation forms for matching."""
    text = unicodedata.normalize("NFKC", text)
    for ch in ("‎", "‏", "‫", "‬", "‭", "‮",
               "⁦", "⁧", "⁨", "⁩", "؜"):
        text = text.replace(ch, "")
    return re.sub(r"[ \t]+", " ", text).strip()


def _tesseract(image_bytes: bytes, languages: str = "ara+eng") -> OcrResult | None:
    exe = Path(TESSERACT_BIN)
    if not exe.exists():
        return None
    # Tesseract requires a real input file. Passing "stdin" silently
    # produced empty output on every call.
    import tempfile
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        proc = subprocess.run(
            [str(exe), tmp_path, "stdout", "-l", languages,
             "--tessdata-dir", str(_TESSDATA), "--psm", "6"],
            capture_output=True, timeout=45,
        )
    except Exception:  # noqa: BLE001
        return None
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
    if proc.returncode != 0:
        return None
    text = proc.stdout.decode("utf-8", errors="replace")
    lines = [{"text": l, "bbox": None, "confidence": None}
             for l in (x.strip() for x in text.splitlines()) if l]
    norm = _normalize(text)
    return OcrResult(
        engine="tesseract",
        text=text.strip(),
        normalized_text=norm,
        confidence=None,  # tesseract TSV parsing omitted; presence is the signal
        has_arabic=bool(_ARABIC_RE.search(norm)),
        lines=lines,
        engines_used=["tesseract"],
    )


def _easyocr(image_bytes: bytes) -> OcrResult | None:
    reader = _OCR_ENGINE.get("reader")
    if reader is None:
        try:
            import easyocr
        except Exception:  # noqa: BLE001
            return None
        reader = easyocr.Reader(["ar", "en"], gpu=False, verbose=False)
        _OCR_ENGINE["reader"] = reader
    try:
        res = reader.readtext(io.BytesIO(image_bytes), detail=1, paragraph=False)
    except Exception:  # noqa: BLE001
        return None
    lines = [{"text": t, "bbox": None, "confidence": round(float(c), 3)}
             for _, t, c in res]
    text = "\n".join(l["text"] for l in lines)
    norm = _normalize(text)
    confs = [l["confidence"] for l in lines if l["confidence"] is not None]
    return OcrResult(
        engine="easyocr",
        text=text,
        normalized_text=norm,
        confidence=round(sum(confs) / len(confs), 3) if confs else None,
        has_arabic=bool(_ARABIC_RE.search(norm)),
        lines=lines,
        engines_used=["easyocr"],
    )


def _merge(primary: OcrResult, fallback: OcrResult) -> OcrResult:
    """
    Combine two engines WITHOUT duplicating text.

    EasyOCR emits RTL script in reversed logical order, so its lines are
    reversed before merging. Lines already present in the primary
    result are dropped rather than appended again.
    """
    def reversed_line(line: str) -> str:
        return line[::-1] if _ARABIC_RE.search(line) else line

    existing = {_normalize(l["text"]) for l in primary.lines}
    merged = list(primary.lines)
    for line in fallback.lines:
        cand = reversed_line(line["text"])
        if _normalize(cand) and _normalize(cand) not in existing:
            existing.add(_normalize(cand))
            merged.append({**line, "text": cand, "sourceEngine": "easyocr"})

    urls = list(primary.urls) or recover_urls(primary.normalized_text)
    known = {u.candidate.lower() for u in urls}
    for u in recover_urls(fallback.normalized_text):
        if u.candidate.lower() not in known:
            known.add(u.candidate.lower())
            urls.append(u)

    return OcrResult(
        engine=f"{primary.engine}+{fallback.engine}",
        text=primary.text,
        normalized_text=primary.normalized_text,
        confidence=primary.confidence,
        has_arabic=primary.has_arabic or fallback.has_arabic,
        lines=merged,
        urls=urls,
        engines_used=primary.engines_used + fallback.engines_used,
        notes=primary.notes + [
            "Arabic fallback engine ran; its lines were merged without "
            "duplication and RTL text was reordered to logical order."
        ],
    )


def run_ocr(image_bytes: bytes, *, force_easyocr: bool = False) -> OcrResult:
    """
    Tesseract first, EasyOCR only when it earns its latency.

    Measured on browser-rendered screenshots: Tesseract reads URLs
    exactly and is ~18x faster, while EasyOCR is materially better on
    Arabic glyphs. So EasyOCR runs only when Arabic is present or the
    primary pass looks incomplete.
    """
    primary = _tesseract(image_bytes)
    if primary is None:
        fallback = _easyocr(image_bytes)
        if fallback is None:
            return OcrResult(engine="none", text="", normalized_text="",
                             confidence=None, has_arabic=False,
                             notes=["No OCR engine available."])
        fallback.urls = recover_urls(fallback.normalized_text)
        fallback.notes.append("Tesseract unavailable; EasyOCR used alone.")
        return fallback

    primary.urls = recover_urls(primary.normalized_text)

    needs_fallback = (
        force_easyocr
        or primary.has_arabic
        or len(primary.normalized_text) < 12
    )
    if not needs_fallback:
        primary.notes.append("Tesseract only; no Arabic script detected.")
        return primary

    fallback = _easyocr(image_bytes)
    if fallback is None:
        primary.notes.append("Arabic detected but the fallback engine is unavailable.")
        return primary
    return _merge(primary, fallback)


# --------------------------------------------------------------------------
# QR
# --------------------------------------------------------------------------

@dataclass
class QrResult:
    payload: str | None
    decode_status: str
    bbox: list[list[int]] | None
    attempt_used: int
    is_url: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload": self.payload,
            "decodeStatus": self.decode_status,
            "bbox": self.bbox,
            "attemptUsed": self.attempt_used,
            "isUrl": self.is_url,
            "notes": self.notes,
        }


def decode_qr(image_bytes: bytes) -> QrResult:
    """
    Multi-attempt QR decode.

    A single attempt is not enough in practice: small or tightly cropped
    codes need upscaling, and OpenCV needs a quiet zone around the
    symbol. Attempts stop at the first success.
    """
    import cv2
    import numpy as np
    from PIL import Image

    detector = cv2.QRCodeDetector()
    notes: list[str] = []

    def attempt(arr: np.ndarray, label: str, index: int):
        try:
            data, pts, _ = detector.detectAndDecode(arr)
        except Exception:  # noqa: BLE001
            return None, None, f"attempt {index} ({label}) failed"
        if data:
            bbox = None
            if pts is not None:
                bbox = [[int(p[0]), int(p[1])] for p in np.asarray(pts).reshape(-1, 2)]
            return data, bbox, None
        return None, None, f"attempt {index} ({label}) found no code"

    try:
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:  # noqa: BLE001
        return QrResult(None, "not_an_image", None, 0, False, ["image could not be decoded"])

    variants: list[tuple[np.ndarray, str]] = []
    base = np.array(pil)
    variants.append((cv2.cvtColor(base, cv2.COLOR_RGB2BGR), "original"))

    # Bounded, fixed attempt list. No loops until success: each extra
    # attempt costs real latency and an unbounded retry is a DoS vector
    # on a user-supplied image.
    for factor in (2.0, 3.0):
        up = cv2.resize(base, None, fx=factor, fy=factor,
                        interpolation=cv2.INTER_CUBIC)
        variants.append((cv2.cvtColor(up, cv2.COLOR_RGB2BGR), f"upscale {factor:g}x"))

    padded = cv2.copyMakeBorder(
        cv2.resize(base, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC),
        60, 60, 60, 60, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    variants.append((cv2.cvtColor(padded, cv2.COLOR_RGB2BGR),
                     "upscale 3x + quiet zone"))

    gray = cv2.cvtColor(padded, cv2.COLOR_RGB2GRAY)
    variants.append((cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR),
                     "upscale 3x + quiet zone + grayscale"))

    # Mild contrast normalisation helps low-contrast printing of a code.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    variants.append((cv2.cvtColor(clahe, cv2.COLOR_GRAY2BGR),
                     "upscale 3x + quiet zone + CLAHE contrast"))

    for idx, (arr, label) in enumerate(variants, start=1):
        data, bbox, note = attempt(arr, label, idx)
        if note:
            notes.append(note)
        if data:
            is_url = data.lower().startswith(("http://", "https://"))
            return QrResult(
                payload=data,
                decode_status="decoded",
                bbox=bbox,
                attempt_used=idx,
                is_url=is_url,
                notes=notes + [f"decoded on attempt {idx}: {label}"],
            )

    return QrResult(None, "not_found", None, len(variants), False,
                    notes + ["no QR symbol decoded across all attempts"])


# --------------------------------------------------------------------------
# Encoded content
# --------------------------------------------------------------------------

# No trailing \b: it cannot match immediately after '=', which silently
# stripped base64 padding and left a length that was no longer a
# multiple of 4, so valid payloads were skipped entirely.
_B64_RE = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/=])")
_B32_RE = re.compile(r"\b[A-Z2-7]{16,}={0,6}\b", re.I)
# 8 byte-pairs minimum, and no trailing \b so a payload that fills the
# string exactly still matches.
_HEX_RE = re.compile(r"(?<![0-9a-fA-F])(?:[0-9a-fA-F]{2}[ :]?){8,}(?![0-9a-fA-F])")
_URLE_ENC_RE = re.compile(r"(?:%[0-9a-fA-F]{2}){4,}")
_UNI_ESC_RE = re.compile(r"(?:\\u[0-9a-fA-F]{4}){3,}")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]*")


@dataclass
class EncodingFinding:
    encoding_type: str
    raw_preview: str
    decoded_preview: str
    confidence: float
    risk_indicators: list[str] = field(default_factory=list)
    depth: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "encodingType": self.encoding_type,
            "rawPreview": self.raw_preview,
            "decodedPreview": self.decoded_preview,
            "confidence": round(self.confidence, 3),
            "riskIndicators": list(self.risk_indicators),
            "depth": self.depth,
        }


def _preview(text: str, limit: int = 160) -> str:
    text = text.strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    good = sum(1 for c in text if c.isprintable() or c in "\r\n\t")
    return good / len(text)


def inspect_encoded(text: str, *, depth: int = 1) -> list[EncodingFinding]:
    """
    Find encoded payloads and decode them for INSPECTION ONLY.

    Decoded bytes are rendered as text when they are mostly printable
    and otherwise reported as binary. Nothing is ever executed,
    deserialised or imported. Recursion is bounded at MAX_DECODE_DEPTH
    and output is bounded at MAX_DECODED_BYTES.
    """
    if depth > MAX_DECODE_DEPTH or not text:
        return []
    findings: list[EncodingFinding] = []

    def add(kind: str, raw: str, decoded: bytes, conf: float, indicators: list[str]) -> None:
        if len(decoded) > MAX_DECODED_BYTES:
            decoded = decoded[:MAX_DECODED_BYTES]
        try:
            shown = decoded.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            shown = repr(decoded[:120])
        findings.append(EncodingFinding(
            encoding_type=kind, raw_preview=_preview(raw),
            decoded_preview=_preview(shown), confidence=conf,
            risk_indicators=indicators, depth=depth,
        ))

    for m in _JWT_RE.finditer(text):
        add("jwt", m.group(0), m.group(0).encode(), 0.95,
            ["JWT-like three-part token structure; header/payload inspected only, "
             "signature not verified and token not used."])
        try:
            import json
            parts = m.group(0).split(".")
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
            findings[-1].decoded_preview = _preview(json.dumps(payload, ensure_ascii=False))
            findings[-1].risk_indicators.append("JWT payload decoded as JSON (not verified).")
        except Exception:  # noqa: BLE001
            pass

    for m in _B64_RE.finditer(text):
        raw = m.group(0)
        if len(raw) % 4:
            continue
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            continue
        if _printable_ratio(decoded.decode("utf-8", "replace")) > 0.85 and len(decoded) > 8:
            add("base64", raw, decoded, 0.8, ["Base64 payload decodes to readable text."])
            findings.extend(inspect_encoded(decoded.decode("utf-8", "replace"),
                                            depth=depth + 1))

    for m in _HEX_RE.finditer(text):
        raw = re.sub(r"[ :]", "", m.group(0))
        try:
            decoded = bytes.fromhex(raw)
        except ValueError:
            continue
        if _printable_ratio(decoded.decode("utf-8", "replace")) > 0.85:
            add("hex", m.group(0), decoded, 0.75, ["Hex-encoded payload decodes to text."])

    for m in _URLE_ENC_RE.finditer(text):
        try:
            from urllib.parse import unquote
            decoded = unquote(m.group(0))
        except Exception:  # noqa: BLE001
            continue
        add("url_encoding", m.group(0), decoded.encode(), 0.7,
            ["Percent-encoded sequence decoded."])

    for m in _UNI_ESC_RE.finditer(text):
        try:
            decoded = m.group(0).encode().decode("unicode_escape")
        except Exception:  # noqa: BLE001
            continue
        add("unicode_escape", m.group(0), decoded.encode(), 0.75,
            ["Unicode escape sequences decoded to characters."])

    for m in _B32_RE.finditer(text):
        raw = m.group(0).upper()
        padded = raw + "=" * ((8 - len(raw) % 8) % 8)
        try:
            decoded = base64.b32decode(padded)
        except Exception:  # noqa: BLE001
            continue
        if _printable_ratio(decoded.decode("utf-8", "replace")) > 0.85:
            add("base32", raw, decoded, 0.65, ["Base32 payload decodes to readable text."])

    return findings
