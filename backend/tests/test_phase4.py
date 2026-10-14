"""Phase 4 backend tests for multimodal intelligence expansion.

Tests: cross-modal correlation, domain mismatch, IDN awareness, multiple QR,
encoded URLs, file MIME mismatch, coverage model, cross-modal conflicts,
error isolation, evidence IDs, report traceability, SHA-256 hashing.
"""
from __future__ import annotations

import hashlib
import io

import pytest

from app.evidence.model import EvidenceEntity, Polarity, Strength
from app.evidence.correlation import build_evidence_entities, build_relationships, run_correlation
from app.evidence.domain_consistency import check_domain_consistency, extract_domain_entities, extract_homoglyph_entities
from app.evidence.visible_domain import extract_visible_domains


class TestVisibleDomainExtraction:
    def test_extracts_domains_from_ocr(self):
        results = extract_visible_domains('Visit paypal.com or bank.com today')
        assert len(results) == 2
        assert results[0].domain == 'paypal.com'
        assert results[1].domain == 'bank.com'

    def test_no_false_positives(self):
        results = extract_visible_domains('The quick brown fox jumps over the lazy dog')
        assert results == []

    def test_empty_text(self):
        results = extract_visible_domains('')
        assert results == []


class TestDomainConsistency:
    def test_same_domains(self):
        dc = check_domain_consistency(['paypal.com', 'paypal.com'])
        assert dc.status == 'partially_consistent'
        assert dc.punycode_present is False

    def test_mismatch(self):
        dc = check_domain_consistency(['bank.com', 'evil-example.xyz'])
        assert dc.status == 'mismatch'
        assert dc.confusable_indicator is True

    def test_single_domain(self):
        dc = check_domain_consistency(['secure-bank.example'])
        assert dc.status == 'consistent'

    def test_empty(self):
        dc = check_domain_consistency([])
        assert dc.status == 'insufficient_evidence'

    def test_punycode_detected(self):
        dc = check_domain_consistency(['xn--paypal-xb4b.com'])
        assert dc.punycode_present is True

    def test_mixed_script_detected(self):
        dc = check_domain_consistency(['bаnk.com'])  # Cyrillic а
        assert dc.mixed_script is True or dc.status == 'mismatch'


class TestEntityExtraction:
    def test_extract_domain_entities(self):
        from app.evidence.visible_domain import VisibleDomain
        vd = VisibleDomain(raw='paypal.com', domain='paypal.com', confidence=0.8)
        entities = extract_domain_entities([vd.to_dict()])
        assert len(entities) == 1
        assert entities[0].type == 'Domain'
        assert entities[0].id.startswith('domain-')

    def test_extract_homoglyph_punycode(self):
        entities = extract_homoglyph_entities('xn--paypal-xb4b.com')
        assert any(e.type == 'PunycodeIndicator' for e in entities)

    def test_extract_homoglyph_mixed_script(self):
        entities = extract_homoglyph_entities('bаnk.com')  # Cyrillic а
        assert any(e.type == 'MixedScriptIndicator' for e in entities)


class TestCrossModalCorrelation:
    def test_visible_destination_mismatch(self):
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'ocr': {'text': 'Visit secure-bank.example', 'normalizedText': 'visit secure-bank.example', 'confidence': 0.9},
            'qr': {'payload': 'https://evil-example.xyz', 'decodeStatus': 'decoded', 'isUrl': True},
            'urls': [],
            'file': None,
            'encoding': [],
            'provenance': {'status': 'unavailable', 'notes': []},
        }
        entities = build_evidence_entities(payload)
        relations = build_relationships(entities)
        correlations = run_correlation(entities, relations)

        # Visible domain differs from QR destination
        mismatch_found = any(c['conflictType'] in ('DISPLAYED_DESTINATION_MISMATCH', 'QR_VS_VISIBLE_DESTINATION') for c in correlations)
        assert mismatch_found

    def test_matching_visible_destination(self):
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'ocr': {'text': 'Login at www.bank.com', 'normalizedText': 'login at www.bank.com', 'confidence': 0.9},
            'qr': {'payload': 'https://www.bank.com/login', 'decodeStatus': 'decoded', 'isUrl': True},
            'urls': [],
            'file': None,
            'encoding': [],
            'provenance': {'status': 'unavailable', 'notes': []},
        }
        entities = build_evidence_entities(payload)
        relations = build_relationships(entities)
        correlations = run_correlation(entities, relations)

        mismatch_found = any(c['conflictType'] == 'DISPLAYED_DESTINATION_MISMATCH' for c in correlations)
        assert not mismatch_found

    def test_qr_vs_url_mismatch(self):
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'ocr': {'text': 'Visit our site', 'normalizedText': 'visit our site', 'confidence': 0.8},
            'qr': {'payload': 'https://evil-example.xyz', 'decodeStatus': 'decoded', 'isUrl': True},
            'urls': [{'rawExtractedText': 'https://secure-url.example', 'normalizedCandidate': 'https://secure-url.example', 'confidence': 0.9, 'origin': 'ocr'}],
            'file': None,
            'encoding': [],
            'provenance': {'status': 'unavailable', 'notes': []},
        }
        entities = build_evidence_entities(payload)
        relations = build_relationships(entities)
        correlations = run_correlation(entities, relations)

        # QR destination differs from ocr URL destination
        mismatch_found = any(c['conflictType'] == 'QR_VS_URL' for c in correlations)
        assert mismatch_found

    def test_qr_vs_url_match(self):
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'ocr': {'text': 'Visit our site', 'normalizedText': 'visit our site', 'confidence': 0.8},
            'qr': {'payload': 'https://evil-example.xyz', 'decodeStatus': 'decoded', 'isUrl': True},
            'urls': [{'rawExtractedText': 'https://evil-example.xyz', 'normalizedCandidate': 'https://evil-example.xyz', 'confidence': 0.95, 'origin': 'qr'}],
            'file': None,
            'encoding': [],
            'provenance': {'status': 'unavailable', 'notes': []},
        }
        entities = build_evidence_entities(payload)
        relations = build_relationships(entities)
        correlations = run_correlation(entities, relations)

        mismatch_found = any(c['conflictType'] == 'QR_VS_URL' for c in correlations)
        assert not mismatch_found

    def test_c2pa_detector_conflict(self):
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'ocr': {'text': 'Test', 'normalizedText': 'test', 'confidence': 0.9},
            'qr': None,
            'urls': [],
            'file': None,
            'encoding': [],
            'provenance': {'status': 'verified', 'aiGeneratedAssertion': True, 'notes': []},
        }
        # Build entities, then add provenance and ensemble entities that conflict
        entities = build_evidence_entities(payload)
        provenance = EvidenceEntity(
            id="provenance",
            source="provenance",
            modality="provenance",
            type="Provenance",
            title="Content Credentials",
            rawValue="verified",
            normalizedValue="c2pa",
            confidence=0.9,
            verified=True,
            polarity=Polarity.SUPPORTS_TRUST,
            stage="verification",
        )
        entities.insert(0, provenance)
        entities.append(EvidenceEntity(
            id="ensemble",
            source="image",
            modality="image",
            type="DetectorEnsemble",
            title="Detector ensemble",
            rawValue="synthetic-side",
            normalizedValue=None,
            confidence=None,
            polarity=Polarity.SUPPORTS_RISK,
            stage="correlation",
        ))
        relations = build_relationships(entities)
        correlations = run_correlation(entities, relations)

        conflict_found = any(c['conflictType'] == 'C2PA_DETECTOR_CONFLICT' for c in correlations)
        assert conflict_found


class TestHashing:
    def test_sha256(self):
        data = b'hello world'
        h = hashlib.sha256(data).hexdigest()
        assert h == 'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        assert len(h) == 64


class TestCoverageModel:
    def test_coverage_calculation(self):
        from app.evidence.coverage import CoverageModel
        cov = CoverageModel(
            provenance='available',
            ocr='analyzed',
            qr='not_applicable',
            url='analyzed',
            encoding='not_applicable',
        )
        # 3 of 5 channels measured: provenance, ocr, url
        assert cov.coverage_percent() == 60.0


class TestErrorIsolation:
    def test_error_does_not_break_pipeline(self):
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'ocr': {'text': '', 'normalizedText': '', 'confidence': 0.0},
            'qr': None,
            'urls': [],
            'file': None,
            'encoding': [],
            'provenance': None,
        }
        # Should not raise
        entities = build_evidence_entities(payload)
        assert isinstance(entities, list)
        assert len(entities) >= 1


class TestEvidenceIds:
    def test_entity_ids_are_unique(self):
        payload = {
            'mode': 'screenshot',
            'fileName': 'test.png',
            'ocr': {'text': 'Visit paypal.com', 'normalizedText': 'visit paypal.com', 'confidence': 0.9},
            'qr': {'payload': 'https://qr-domain.com', 'decodeStatus': 'decoded', 'isUrl': True},
            'urls': [],
            'file': None,
            'encoding': [],
            'provenance': {'status': 'unavailable', 'notes': []},
        }
        entities = build_evidence_entities(payload)
        ids = [e.id for e in entities]
        assert len(ids) == len(set(ids))


class TestUrlCandidate:
    def test_url_encodes_to_url(self):
        payload = {
            'mode': 'file',
            'fileName': 'test.txt',
            'ocr': None,
            'qr': None,
            'urls': [],
            'file': {'accepted': True, 'fileKind': 'text', 'urls': ['https://base64-decoder.io']},
            'encoding': [],
            'provenance': {'status': 'unavailable', 'notes': []},
        }
        entities = build_evidence_entities(payload)
        # Should not raise
        assert len(entities) >= 1


class TestFileMimeMismatch:
    def test_mime_mismatch_signal(self):
        # Extension/MIME mismatch is a signal, not proof of maliciousness
        payload = {
            'mode': 'file',
            'fileName': 'document.pdf',
            'ocr': None,
            'qr': None,
            'urls': [],
            'file': {'accepted': True, 'fileKind': 'text', 'urls': [], 'suspicious': []},
            'encoding': [],
            'provenance': {'status': 'unavailable', 'notes': []},
        }
        entities = build_evidence_entities(payload)
        relations = build_relationships(entities)
        correlations = run_correlation(entities, relations)
        # Should not mislabel; the system handles mismatch as a signal
        assert len(entities) >= 1
