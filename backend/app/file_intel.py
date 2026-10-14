"""
Safe file intelligence for the declared, text-like formats only.

Scope is deliberately narrow. BASIRAH inspects files; it never runs
them. Executables, scripts, macros and document-embedded JavaScript are
REJECTED rather than parsed, because the act of parsing them safely is
the hard part and the value is low for a trust-analysis platform.

Rejected outright:
    .exe .dll .scr .com .bat .cmd .ps1 .vbs .js .jar .msi .hta .psm1
    .docm .xlsm .pptm            (macro-enabled containers)

Inspected read-only:
    .txt .json .csv .log .md .yaml .yml .xml .html .htm
    .pdf                          (text + metadata + URLs only)

Every decoded payload stays inert. Nothing is deserialised, imported or
evaluated, and a JSON file is parsed with a size-bounded reader rather
than handed to a permissive loader.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 400_000
MAX_JSON_DEPTH = 12

TEXT_EXTS = {".txt", ".json", ".csv", ".log", ".md", ".yaml", ".yml",
             ".xml", ".html", ".htm", ".ini", ".cfg", ".conf"}
PDF_EXTS = {".pdf"}

# Formats BASIRAH will not touch, with the reason surfaced to the user.
BLOCKED_EXTS = {
    ".exe": "executable", ".dll": "executable", ".scr": "executable",
    ".com": "executable", ".bat": "script", ".cmd": "script",
    ".ps1": "script", ".psm1": "script", ".vbs": "script",
    ".js": "script", ".jse": "script", ".jar": "executable",
    ".msi": "executable", ".hta": "script", ".sh": "script",
    ".docm": "macro-enabled document", ".xlsm": "macro-enabled document",
    ".pptm": "macro-enabled document",
}

_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+", re.I)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_BASE64ISH = re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")


@dataclass
class FileIntel:
    accepted: bool
    file_kind: str
    reason: str | None = None
    size_bytes: int = 0
    text_chars: int = 0
    encoding_guess: str | None = None
    structure: dict[str, Any] = field(default_factory=dict)
    urls: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    ips: list[str] = field(default_factory=list)
    suspicious: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    encoded_preview: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "fileKind": self.file_kind,
            "reason": self.reason,
            "sizeBytes": self.size_bytes,
            "textChars": self.text_chars,
            "encodingGuess": self.encoding_guess,
            "structure": self.structure,
            "urls": self.urls,
            "emails": self.emails,
            "ips": self.ips,
            "suspicious": self.suspicious,
            "notes": self.notes,
            "encodedPreview": self.encoded_preview,
        }


def classify(name: str) -> str:
    ext = PurePosixPath(name.lower()).suffix
    if ext in BLOCKED_EXTS:
        return "blocked"
    if ext in PDF_EXTS:
        return "pdf"
    if ext in TEXT_EXTS:
        return "text"
    return "unsupported"


def _decode(data: bytes) -> tuple[str, str]:
    """Decode with a declared-encoding guess; never raise."""
    for enc in ("utf-8", "utf-8-sig", "cp1256", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8(replaced)"


def _walk_json(node: Any, depth: int = 0) -> dict[str, Any]:
    """
    Summarise JSON structure with a hard depth bound.

    A hostile file can nest thousands of levels deep and exhaust the
    interpreter stack, so recursion stops at MAX_JSON_DEPTH and the
    remainder is reported as truncated rather than walked.
    """
    out: dict[str, Any] = {"type": type(node).__name__}
    if depth >= MAX_JSON_DEPTH:
        out["truncated"] = True
        return out
    if isinstance(node, dict):
        keys = list(node.keys())[:64]
        out["keys"] = keys
        out["keyCount"] = len(node)
        out["nested"] = {k: _walk_json(node[k], depth + 1) for k in keys[:16]
                         if isinstance(node[k], (dict, list))}
    elif isinstance(node, list):
        out["length"] = len(node)
        if node:
            out["sampleType"] = type(node[0]).__name__
    return out


def inspect_file(data: bytes, filename: str) -> FileIntel:
    """
    Inspect an uploaded file read-only.

    Returns an honest refusal for anything outside the declared safe
    set rather than attempting a partial parse.
    """
    kind = classify(filename)
    size = len(data)

    if kind == "blocked":
        ext = PurePosixPath(filename.lower()).suffix
        return FileIntel(
            accepted=False,
            file_kind=BLOCKED_EXTS.get(ext, "unsupported"),
            size_bytes=size,
            reason=(
                f"{ext} files are not inspected. Executables, scripts and "
                "macro-enabled documents are refused because BASIRAH does "
                "not execute uploaded content."
            ),
        )
    if kind == "unsupported":
        ext = PurePosixPath(filename.lower()).suffix or "(no extension)"
        return FileIntel(
            accepted=False, file_kind="unsupported", size_bytes=size,
            reason=(
                f"{ext} is not a supported inspection format. Supported: "
                + ", ".join(sorted(TEXT_EXTS | PDF_EXTS))
            ),
        )
    if size == 0:
        return FileIntel(accepted=False, file_kind=kind, size_bytes=0,
                         reason="file is empty")
    if size > MAX_FILE_BYTES:
        return FileIntel(
            accepted=False, file_kind=kind, size_bytes=size,
            reason=f"file exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB inspection limit",
        )

    if kind == "pdf":
        return _inspect_pdf(data)

    text, encoding = _decode(data)
    truncated = len(text) > MAX_TEXT_CHARS
    if truncated:
        text = text[:MAX_TEXT_CHARS]
        intel = None
    else:
        intel = None

    ext = PurePosixPath(filename.lower()).suffix
    urls = sorted({u.rstrip(".,;'\")]}") for u in _URL_RE.findall(text)})
    emails = sorted(set(_EMAIL_RE.findall(text)))[:50]
    ips = sorted({ip for ip in _IP_RE.findall(text)
                  if all(0 <= int(p) <= 255 for p in ip.split("."))})[:50]

    suspicious: list[str] = []
    structure: dict[str, Any] = {"extension": ext}

    low = text.lower()
    # Inert string patterns only. Nothing here is executed.
    for pattern, label in (
        (r"\bpowershell\b[^\n]{0,80}\b(iex|invoke-expression|downloadstring)\b",
         "PowerShell download/execution string"),
        (r"\bcurl\b[^\n|]{0,80}\|\s*(ba)?sh\b", "curl piped to a shell"),
        (r"\beval\s*\(", "eval( call"),
        (r"\bexec\s*\(", "exec( call"),
        (r"\bbase64_decode\s*\(", "base64_decode call"),
        (r"frombase64string\s*\(", ".NET FromBase64String call"),
        (r"\bimport\s+os\b[^\n]*\bsystem\b", "process/system access"),
        (r"__import__\s*\(", "Python __import__ call"),
        (r"\brm\s+-rf\b", "recursive delete command"),
    ):
        # Both sides are lowercased. Matching a pattern containing
        # capitals against lowercased text with a case-sensitive regex
        # can never fire, which silently disabled this whole rule.
        if re.search(pattern.lower(), low):
            suspicious.append(label)

    if ext == ".json":
        try:
            parsed = json.loads(text)
            structure["json"] = _walk_json(parsed)
            if isinstance(parsed, dict) and len(parsed) > 200:
                suspicious.append(f"unusually large JSON object ({len(parsed)} keys)")
        except Exception as exc:  # noqa: BLE001
            structure["json"] = {"parseError": type(exc).__name__}
            notes = [f"JSON did not parse ({type(exc).__name__}); inspected as plain text."]
            intel = None
            suspicious.append("JSON parse failure")

    elif ext == ".csv":
        try:
            rows = list(csv.reader(io.StringIO(text)))
            structure["csv"] = {
                "rows": len(rows),
                "columns": len(rows[0]) if rows else 0,
                "header": rows[0][:32] if rows else [],
            }
        except Exception as exc:  # noqa: BLE001
            structure["csv"] = {"parseError": type(exc).__name__}

    notes: list[str] = []
    if truncated:
        notes.append(f"content truncated to {MAX_TEXT_CHARS} characters for inspection")
    if not urls:
        notes.append("no URLs found in the visible text")
    # Any C0 control byte other than tab/newline/carriage-return means
    # the "text" file is probably not text.
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
        notes.append("control characters present; file may be binary mislabelled")

    from app.content_intel import inspect_encoded
    encoded = [f.to_dict() for f in inspect_encoded(text)]

    return FileIntel(
        accepted=True,
        file_kind=kind,
        size_bytes=size,
        text_chars=len(text),
        encoding_guess=encoding,
        structure=structure,
        urls=urls,
        emails=emails,
        ips=ips,
        suspicious=suspicious,
        notes=notes,
        encoded_preview=encoded,
    )


def _inspect_pdf(data: bytes) -> FileIntel:
    """
    PDF text and metadata only.

    Deliberately NOT used: any JavaScript action, embedded file
    attachment, launch action or URI action. Those are the parts of a
    PDF that can do something, and inspecting them is out of scope.
    """
    intel = FileIntel(accepted=True, file_kind="pdf", size_bytes=len(data))
    intel.notes.append(
        "PDF inspected for text, metadata and URLs only. Embedded "
        "JavaScript, attachments and launch/URI actions are not parsed "
        "or executed."
    )
    try:
        from pypdf import PdfReader
    except Exception:  # noqa: BLE001
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:  # noqa: BLE001
            intel.accepted = False
            intel.reason = "no PDF text library available (pypdf not installed)"
            return intel

    try:
        reader = PdfReader(io.BytesIO(data))
        intel.structure["pages"] = len(reader.pages)
        meta = reader.metadata or {}
        intel.structure["metadata"] = {
            str(k).lstrip("/"): str(v)[:120] for k, v in list(meta.items())[:20]
        }
        chunks: list[str] = []
        for page in reader.pages[:50]:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                continue
        text = "\n".join(chunks)[:MAX_TEXT_CHARS]
        intel.text_chars = len(text)
        intel.encoding_guess = "pdf-text"
        intel.urls = sorted({u.rstrip(".,;'\")]}") for u in _URL_RE.findall(text)})
        intel.emails = sorted(set(_EMAIL_RE.findall(text)))[:50]
        if not text.strip():
            intel.notes.append(
                "no extractable text layer; the PDF may be image-only"
            )
    except Exception as exc:  # noqa: BLE001
        intel.accepted = False
        intel.reason = f"PDF could not be parsed: {type(exc).__name__}"

    return intel
