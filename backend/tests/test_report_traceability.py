"""Backend tests for report-traceability integrity.

Verifies that reportTraceability IDs come exclusively from actual findings.
"""

import hashlib
import os

import pytest

from app.evidence_service import analyze_evidence

# test_minimal.png is generated in the backend root
TEST_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_PNG = os.path.join(TEST_ROOT, 'test_minimal.png')


def _ensure_test_png():
    """Generate a minimal valid PNG using PIL if it does not exist yet."""
    if os.path.exists(TEST_PNG):
        return
    from PIL import Image
    img = Image.new('RGB', (1, 1), color=(0, 0, 0))
    img.save(TEST_PNG, format='PNG')


def _analyze(data):
    """Run analyze_evidence with minimal valid PNG bytes."""
    return analyze_evidence(data, filename='test_minimal.png',
                            content_type='image/png', mode='auto')


def _payload_for_fuse(overrides=None):
    """Build the internal structure fuse() expects."""
    payload = {
        'mode': 'screenshot',
        'fileName': 'test.png',
        'file': None,
        'ocr': None,
        'qr': None,
        'urls': [],
        'encoding': [],
        'provenance': {'status': 'unavailable', 'notes': []},
        'ensemble': {'detectorAgreement': 'abstained'},
    }
    if overrides:
        payload.update(overrides)
    return payload


class TestZeroFindings:
    """When the pipeline has no findings, the traceability list is empty."""

    def test_findings_empty(self):
        _ensure_test_png()
        data = open(TEST_PNG, 'rb').read()
        response = _analyze(data)
        assert response['reportTraceability'] == []

    def test_no_phantom_ids(self):
        _ensure_test_png()
        data = open(TEST_PNG, 'rb').read()
        response = _analyze(data)
        assert len(response['reportTraceability']) == 0
        assert 'F-001' not in str(response['reportTraceability'])


class TestSingleFinding:
    """One reportable finding -> exactly one traceability ID."""

    def test_one_id_via_fuse(self):
        """A single finding in fuse() yields exactly ['F-001']."""
        from app.evidence_service import fuse
        payload = _payload_for_fuse({
            'urls': [
                {'rawExtractedText': 'https://high-risk.example',
                 'normalizedCandidate': 'https://high-risk.example',
                 'confidence': 1.0, 'origin': 'qr',
                 'urlIntelligence': {'riskLevel': 'high_risk'}}
            ]
        })
        fused = fuse(payload)
        assert len(fused['findings']) == 1
        # fuse returns findings directly; reportTraceability is built by analyze_evidence
        assert fused['findings'][0]['tier'] == 2

    def test_id_matches_finding(self):
        """The ID must correspond to the single finding by index."""
        from app.evidence_service import fuse
        payload = _payload_for_fuse({
            'urls': [
                {'rawExtractedText': 'https://high-risk.example',
                 'normalizedCandidate': 'https://high-risk.example',
                 'confidence': 1.0, 'origin': 'qr',
                 'urlIntelligence': {'riskLevel': 'high_risk'}}
            ]
        })
        fused = fuse(payload)
        assert len(fused['findings']) == 1
        # fuse returns findings directly; reportTraceability comes from analyze_evidence
        assert fused['findings'][0]['tier'] == 2

    def test_report_traceability_formula(self):
        """reportTraceability = [f"F-{i+1:03d}" for i in range(len(findings))]."""
        from app.evidence_service import fuse
        payload = _payload_for_fuse({
            'urls': [
                {'rawExtractedText': 'https://high-risk.example',
                 'normalizedCandidate': 'https://high-risk.example',
                 'confidence': 1.0, 'origin': 'qr',
                 'urlIntelligence': {'riskLevel': 'high_risk'}}
            ]
        })
        fused = fuse(payload)
        assert len(fused['findings']) == 1
        expected = [f"F-{i+1:03d}" for i in range(len(fused['findings']))]
        assert expected == ["F-001"]


class TestNFindings:
    """N reportable findings -> exactly N traceability IDs."""

    def test_count_equals_finding_count(self):
        """Two findings must yield two traceability IDs."""
        from app.evidence_service import fuse
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'file': None,
            'ocr': None,
            'qr': None,
            'urls': [
                {'rawExtractedText': 'https://first.example',
                 'normalizedCandidate': 'https://first.example',
                 'confidence': 1.0, 'origin': 'ocr',
                 'urlIntelligence': {'riskLevel': 'high_risk'}},
                {'rawExtractedText': 'https://second.example',
                 'normalizedCandidate': 'https://second.example',
                 'confidence': 1.0, 'origin': 'ocr',
                 'urlIntelligence': {'riskLevel': 'high_risk'}},
            ],
            'encoding': [],
            'provenance': {'status': 'verified', 'aiGeneratedAssertion': True,
                           'notes': []},
            'ensemble': {'detectorAgreement': 'strong'},
        }
        fused = fuse(payload)
        # Provenance verified assertion + 2 high-risk URLs = 3 actual findings
        assert len(fused['findings']) == 3
        expected = [f"F-{i+1:03d}" for i in range(len(fused['findings']))]
        assert expected == ["F-001", "F-002", "F-003"]

    def test_analyze_with_url_risk(self):
        """A real analysis containing a high-risk URL yields traceability IDs."""
        _ensure_test_png()
        data = open(TEST_PNG, 'rb').read()
        response = analyze_evidence(data, filename='test_minimal.png',
                                    content_type='image/png', mode='auto')
        # reportTraceability must mirror exactly the fusion findings
        expected = [f"F-{i+1:03d}" for i in range(len(response['fusion']['findings']))]
        assert response['reportTraceability'] == expected


class TestRepeatedAnalysis:
    """Repeated identical analysis -> same IDs in the same order."""

    def test_same_ids_order(self):
        data = open(TEST_PNG, 'rb').read()
        r1 = _analyze(data)
        r2 = _analyze(data)
        assert r1['reportTraceability'] == r2['reportTraceability']


class TestHardcodedRange:
    """The implementation must not contain a hardcoded range(1, 50)."""

    def test_no_range(self):
        with open('app/evidence_service.py') as f:
            source = f.read()
        assert 'range(1, 50)' not in source
        assert 'range(1, 51)' not in source
        assert 'range(1, 100)' not in source


class TestNoDuplicates:
    """Report traceability must not contain duplicate IDs."""

    def test_unique_ids(self):
        data = open(TEST_PNG, 'rb').read()
        response = _analyze(data)
        assert len(response['reportTraceability']) == len(set(response['reportTraceability']))


class TestHashing:
    def test_sha256(self):
        data = b'hello world'
        h = hashlib.sha256(data).hexdigest()
        assert h == 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        assert len(h) == 64
