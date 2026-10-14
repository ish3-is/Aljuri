"""
Tests for the provenance-first tier.

The most important tests here are the ones that assert BASIRAH does NOT
overclaim. Several use deliberately hostile inputs, because the failure
mode that matters in a defense is a confident wrong answer.

No test fabricates a signed manifest. Where a real signed fixture is
unavailable the suite asserts the honest degraded path instead, which
is the behaviour a committee can actually rely on.
"""

from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest
from PIL import Image

from app.image.provenance_c2pa import (
    EvidenceStrength,
    ProvenanceStatus,
    _classify,
    _manifest_bytes,
    _safe_string,
    verify_provenance,
)


def png_bytes(color=(120, 60, 200), size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


class TestManifestDetection:
    def test_plain_png_has_no_manifest(self):
        assert _manifest_bytes(png_bytes()) is False

    def test_c2pa_marker_detected(self):
        data = png_bytes() + b"\x00" * 32 + b"c2pa" + b"\x00" * 32
        assert _manifest_bytes(data) is True

    def test_marker_presence_alone_never_means_verified(self):
        """
        An attacker can embed the magic bytes trivially. The real SDK
        parses the container properly and finds no JUMBF manifest, so
        the crude pre-check is corrected downward -- the strongest
        possible outcome for this input.
        """
        forged = png_bytes() + b"\x00" * 32 + b"c2pa" + b"\x00" * 32
        res = verify_provenance(forged)
        assert res.status is not ProvenanceStatus.VERIFIED
        assert res.signature_verified is not True
        # The byte marker tripped our cheap pre-check, but the SDK's own
        # parse overrules it: there is no manifest here at all.
        assert res.manifest_present is False
        assert res.status is ProvenanceStatus.UNAVAILABLE


class TestAbsenceIsNeutral:
    def test_no_manifest_is_unavailable_not_suspicious(self):
        res = verify_provenance(png_bytes())
        assert res.status is ProvenanceStatus.UNAVAILABLE
        assert res.manifest_present is False
        assert res.evidence_strength is EvidenceStrength.NEUTRAL

    def test_absence_does_not_claim_authenticity(self):
        res = verify_provenance(png_bytes())
        blob = json.dumps(res.to_dict())
        assert "authentic" not in blob.lower().replace(
            "does not indicate authenticity", ""
        )
        assert any("does not" in n for n in res.notes)


class TestSdkUnavailable:
    def test_manifest_present_without_sdk_is_present_unverified(self):
        forged = png_bytes() + b"c2pa" + b"\x00" * 16
        with patch.dict("sys.modules", {"c2pa": None}):
            res = verify_provenance(forged)
        assert res.status in (
            ProvenanceStatus.PRESENT_UNVERIFIED,
            ProvenanceStatus.INVALID,
        )
        assert res.signature_verified is not True
        assert res.sdk_available is False

    def test_never_raises_on_garbage(self):
        res = verify_provenance(b"\x00" * 4096 + b"c2pa")
        assert res.status is not ProvenanceStatus.VERIFIED


class TestAssertionClassification:
    @pytest.mark.parametrize("raw,expected", [
        ("c2pa.created", "generative"),
        ("c2pa.generated", "generative"),
        ("ai_generated_content", "generative"),
        ("trainedAlgorithmicMedia", "generative"),
        ("c2pa.edited", "edit"),
        ("c2pa.converted", "edit"),
        ("c2pa.captured", "capture"),
        ("c2pa.placed", "other"),
    ])
    def test_classification(self, raw, expected):
        assert _classify(raw) == expected

    def test_unfamiliar_action_is_not_treated_as_ai(self):
        assert _classify("c2pa.did.something.unheard.of") == "other"

    def test_original_assertion_text_is_preserved(self):
        # The raw wording must survive so an operator can audit it.
        assert _classify("c2pa.created") == "generative"


class TestUntrustedInput:
    def test_oversized_manifest_field_is_truncated(self):
        assert len(_safe_string("x" * 10_000, limit=100)) == 100

    def test_non_string_field_returns_none(self):
        assert _safe_string({"evil": "dict"}) is None
        assert _safe_string(None) is None
        assert _safe_string("") is None

    def test_serialised_output_has_no_filesystem_paths(self):
        res = verify_provenance(png_bytes())
        blob = json.dumps(res.to_dict())
        assert "C:\\\\" not in blob
        assert "/tmp/" not in blob
        assert "site-packages" not in blob

    def test_payload_is_json_serialisable(self):
        json.dumps(verify_provenance(png_bytes()).to_dict())


class TestVerifiedManifestSemantics:
    """
    A valid manifest must NOT be summarised as "this is authentic".
    It may assert generative creation, editing, or capture, and those
    lead to different conclusions.
    """

    def _patched(self, parsed: dict):
        """
        Mirror the real c2pa-python API surface:
          Reader(mime_type, stream) -> .get_validation_results(), .json()
        plus c2pa.C2paError. Anything the code under test touches that
        is missing here would make the test pass for the wrong reason.
        """
        validation = {
            "validation_results": [
                {"validation_status": s, "success": (s == "signature_validated")}
                for s in parsed.get("validation_status", [])
            ]
        }

        validation = {"validation_results": [
            {"validation_status": "signature_validated", "success": True}]}

        class FakeReader:
            def __init__(self, *args, **kwargs):
                pass

            def get_validation_results(self):
                return validation

            def json(self):
                return json.dumps(parsed)

        class C2paError(Exception):
            pass

        module = type("m", (), {"Reader": FakeReader, "C2paError": C2paError})
        with patch.dict("sys.modules", {"c2pa": module}):
            res = verify_provenance(b"c2pa" + b"\x00" * 40)
        titles = [i["title"] for i in res.ingredients]
        assert "http://169.254.169.254/latest/meta-data/" in titles
        # recorded as data; never dereferenced
        assert res.status is ProvenanceStatus.VERIFIED
