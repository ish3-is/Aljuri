"""
Centralised runtime-model preflight.

Verifies the three Git LFS runtime binaries are present, non-empty and no
longer pointer text before the service is allowed to start.  A model that is
still an LFS pointer is NOT a loadable artefact, so the preflight must reject
it instead of letting the service boot with a broken model.

This module is ALSO used as the source of the deployment-readiness fields
reported by GET /health, so a single place owns both the preflight and the
health disclosure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import MODELS_DIR

logger = logging.getLogger(__name__)

# The three runtime binaries that must be real pickled/.pt artefacts, not
# Git LFS pointer text.  `models/url_risk_model.joblib` is the legacy
# Phase 2 name; the active production bundle is now named by
# `models/ACTIVE_MODEL.json`, so we probe that pointer instead of assuming a
# hard-coded filename.
REQUIRED_RUNTIMES: list[tuple[str, str]] = [
    ("basirah-url-v3.joblib", "basirah-url-v3.joblib"),
    ("detector_b_clip_probe.joblib", "detector_b_clip_probe.joblib"),
    ("multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt", "multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt"),
]

MIN_FILE_SIZE = 16_384  # 16 KiB — far below any real model, well above a
#  pointer file (a Git LFS pointer is ~100 bytes).  Catches a
#  zero-byte or truncated artifact without hard-coding a weight.

_LFS_POINTER_HEADER = b"version https://git-lfs.github.com/spec/v1"


@dataclass(frozen=True)
class ModelReadiness:
    """Outcome of a single runtime-model preflight check."""

    name: str
    exists: bool
    is_file: bool
    size: int
    minimum_size: int
    is_lfs_pointer: bool
    readable: bool
    reason: str | None = None

    @property
    def available(self) -> bool:
        """True when the model is present, real, non-empty and not a pointer."""
        return self.exists and self.is_file and self.size >= self.minimum_size and not self.is_lfs_pointer


@dataclass(frozen=True)
class ModelReadinessReport:
    """Aggregated preflight result for all three runtime binaries."""

    models: list[ModelReadiness]
    all_available: bool
    missing: list[str] = field(default_factory=list)
    zero_byte: list[str] = field(default_factory=list)
    lfs_pointers: list[str] = field(default_factory=list)
    unopenable: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """True when every runtime model is available."""
        return self.all_available


def _read_first_bytes(path: Path, n: int = 120) -> bytes:
    """Read the first n bytes without loading the whole file."""
    try:
        with path.open("rb") as fh:
            return fh.read(n)
    except OSError:
        return b""


def check_model(path: Path, minimum_size: int = MIN_FILE_SIZE) -> ModelReadiness:
    """Verify a single model file is a real artefact and not an LFS pointer."""
    name = path.name
    if not path.exists():
        return ModelReadiness(
            name=name,
            exists=False,
            is_file=False,
            size=0,
            minimum_size=minimum_size,
            is_lfs_pointer=False,
            readable=False,
            reason="missing",
        )

    if not path.is_file():
        return ModelReadiness(
            name=name,
            exists=True,
            is_file=False,
            size=path.stat().st_size,
            minimum_size=minimum_size,
            is_lfs_pointer=False,
            readable=False,
            reason="not_a_regular_file",
        )

    size = path.stat().st_size
    if size == 0:
        return ModelReadiness(
            name=name,
            exists=True,
            is_file=True,
            size=0,
            minimum_size=minimum_size,
            is_lfs_pointer=False,
            readable=False,
            reason="zero_bytes",
        )

    head = _read_first_bytes(path)
    is_pointer = head.startswith(_LFS_POINTER_HEADER)

    if is_pointer:
        return ModelReadiness(
            name=name,
            exists=True,
            is_file=True,
            size=size,
            minimum_size=minimum_size,
            is_lfs_pointer=True,
            readable=False,
            reason="still_a_git_lfs_pointer",
        )

    # Verify it opens and yields content (catches a truncated file that
    # happens not to begin with the pointer header).
    try:
        with path.open("rb") as fh:
            fh.seek(0)
            chunk = fh.read(min(size, 4096))
        readable = len(chunk) > 0
    except OSError as exc:
        logger.error("Cannot open model file %s: %s", path, exc)
        readable = False
        reason = f"unreadable: {exc}"

    return ModelReadiness(
        name=name,
        exists=True,
        is_file=True,
        size=size,
        minimum_size=minimum_size,
        is_lfs_pointer=False,
        readable=readable,
        reason=reason if not readable else None,
    )


def preflight_models(
    models_dir: Path = MODELS_DIR,
    minimum_size: int = MIN_FILE_SIZE,
) -> ModelReadinessReport:
    """Run the preflight against the three required runtime binaries.

    Returns an aggregate report.  Callers can inspect `all_available` and the
    per-model `ModelReadiness` before permitting startup.
    """
    missing, zero_byte, lfs_pointers, unopenable = [], [], [], []

    results = []
    for rel_name, display_name in REQUIRED_RUNTIMES:
        path = models_dir / rel_name
        readiness = check_model(path, minimum_size=minimum_size)
        results.append(readiness)

        if not readiness.available:
            if not path.exists():
                missing.append(display_name)
            elif readiness.size == 0:
                zero_byte.append(display_name)
            elif readiness.is_lfs_pointer:
                lfs_pointers.append(display_name)
            elif not readiness.readable:
                unopenable.append(display_name)

    all_available = (
        len(missing) == 0
        and len(zero_byte) == 0
        and len(lfs_pointers) == 0
        and len(unopenable) == 0
    )

    return ModelReadinessReport(
        models=results,
        all_available=all_available,
        missing=missing,
        zero_byte=zero_byte,
        lfs_pointers=lfs_pointers,
        unopenable=unopenable,
    )


def policy_check() -> tuple[bool, str]:
    """Return (startup_allowed, reason) for the chosen startup policy.

    With STRICT_STARTUP the service fails to start if any mandatory runtime
    model is unresolved.  This is the policy BASIRAH uses for its three
    runtime-required models.
    """
    report = preflight_models()
    if report.ready:
        return True, "all runtime models verified"
    reasons = []
    if report.missing:
        reasons.append(f"missing: {', '.join(report.missing)}")
    if report.zero_byte:
        reasons.append(f"zero-byte: {', '.join(report.zero_byte)}")
    if report.lfs_pointers:
        reasons.append(f"git-lfs-pointer: {', '.join(report.lfs_pointers)}")
    if report.unopenable:
        reasons.append(f"unreadable: {', '.join(report.unopenable)}")
    return False, "; ".join(reasons)


def health_readiness() -> dict:
    """Structured model readiness for GET /health, no filesystem paths.

    Callers must NOT include the `path` field in the response — this module
    only reports `available`/`reason` at the model-owner level.
    """
    report = preflight_models()
    return {
        "ready": report.all_available,
        "models": {
            m.name: {
                "available": m.available,
                "reason": m.reason,
            }
            for m in report.models
        },
        "issues": {
            "missing": report.missing,
            "zero_byte": report.zero_byte,
            "lfs_pointers": report.lfs_pointers,
            "unopenable": report.unopenable,
        },
    }
