"""
Provenance interface.

This module deliberately ships the *schema* for content provenance
without claiming verification it cannot perform.

C2PA / Content Credentials are cryptographically signed manifests that
can establish who created or edited a file. Verifying them properly means
validating a certificate chain against trust anchors, checking claim
signatures, and applying the full C2PA conformance rules. Doing that
partially is worse than not doing it: a "verified" badge that only
checked for the presence of a manifest is a false assurance, and this
project's whole Phase 2 arc was spent learning that a plausible-looking
signal can encode something other than what it appears to.

So the interface is real, the statuses are real, and the one thing that
cannot be done locally today reports `unavailable` with a reason.

Status semantics
----------------
``verified``            not issued by this implementation
``present_unverified``  a C2PA manifest is present but not validated
``invalid``             a manifest is present and failed parsing
``unavailable``         no manifest found
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class ProvenanceStatus(str, Enum):
    VERIFIED = "verified"
    PRESENT_UNVERIFIED = "present_unverified"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


@dataclass
class ProvenanceResult:
    status: ProvenanceStatus
    content_credentials_present: bool
    manifest_bytes: int = 0
    manifest_found: bool = False
    claim_generator: str | None = None
    claimed_software: str | None = None
    #: Why we are not able to say more. Always populated for non-verified.
    limitation: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


# C2PA boxes we look for by name in the JPEG APP11 / PNG iTXt segments.
_C2PA_MARKERS = (b"c2pa", b"jumb", b"c2pa.assertion")
_CAI_MARKER = b"c2pa"


def _scan_for_manifest(data: bytes) -> tuple[bool, int]:
    """Detect a C2PA/JUMBF manifest without parsing or trusting it."""
    lowered = data[:2_000_000].lower()
    for marker in _C2PA_MARKERS:
        index = lowered.find(marker)
        if index != -1:
            return True, index
    return False, -1


def inspect_provenance(data: bytes) -> ProvenanceResult:
    """Report what provenance evidence exists, without fabricating any."""
    found, offset = _scan_for_manifest(data)

    if not found:
        return ProvenanceResult(
            status=ProvenanceStatus.UNAVAILABLE,
            content_credentials_present=False,
            manifest_found=False,
            limitation=(
                "No content provenance data was found. Most images have "
                "none, including genuine camera photos that have been "
                "shared through a platform. Absence is not evidence of "
                "synthetic origin."
            ),
        )

    # A manifest is present. We deliberately do NOT parse it into claims.
    # Reading the generator string out of an unvalidated manifest would
    # let any file assert "made with DALL-E" and be believed.
    region = data[offset : offset + 8192]
    generator = None
    claimed_software = None
    try:
        text = region.decode("utf-8", errors="ignore")
        if "claim_generator" in text:
            generator = "declared in unvalidated manifest"
    except Exception:  # noqa: BLE001
        pass

    return ProvenanceResult(
        status=ProvenanceStatus.PRESENT_UNVERIFIED,
        content_credentials_present=True,
        manifest_bytes=len(region),
        manifest_found=True,
        claim_generator=generator,
        claimed_software=claimed_software,
        limitation=(
            "A content-credentials manifest is present but has NOT been "
            "cryptographically validated by this system. Treat the claims "
            "inside it as unverified assertions until checked against a "
            "C2PA trust list."
        ),
    )


def c2pa_verification_deferred() -> dict[str, Any]:
    """Document the deliberate omission of local C2PA verification."""
    return {
        "implemented": False,
        "reason": (
            "Local C2PA verification requires certificate-chain validation "
            "against maintained trust anchors plus full claim-signature "
            "checking. A partial implementation would emit a 'verified' "
            "status it cannot justify."
        ),
        "status_returned_instead": ProvenanceStatus.PRESENT_UNVERIFIED.value,
        "interface_ready": True,
    }
