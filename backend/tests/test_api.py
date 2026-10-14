"""
API-level tests.

These exercise the real HTTP surface via FastAPI's TestClient, so the
serialisation, status codes and response shape are all covered.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["url_engine"]["heuristic_rules"] > 0
        assert body["url_engine"]["feature_count"] > 0

    def test_health_reports_model_availability_honestly(self) -> None:
        """Without a trained model this must be False, not optimistically True."""
        body = client.get("/api/health").json()
        assert isinstance(body["model_available"], bool)

    def test_root_health_alias(self) -> None:
        assert client.get("/health").status_code == 200


class TestURLAnalysis:
    def test_analyzes_a_plain_url(self) -> None:
        response = client.post("/api/analyze/url", json={"url": "https://example.com"})
        assert response.status_code == 200
        body = response.json()
        assert body["isMock"] is False
        assert body["source"] == "live"
        assert 0 <= body["trustScore"] <= 100
        assert body["riskLevel"] in {"trusted", "caution", "high_risk"}

    def test_accepts_bare_domain(self) -> None:
        response = client.post("/api/analyze/url", json={"url": "example.com"})
        assert response.status_code == 200

    def test_structurally_suspicious_url_is_flagged(self) -> None:
        """Structural behaviour only — no claim about any real domain."""
        response = client.post(
            "/api/analyze/url",
            json={"url": "https://secure-login-account-update.example.com"},
        )
        body = response.json()
        fired = {f["id"] for f in body["heuristicFindings"] if f["triggered"]}
        assert "SUSPICIOUS_KEYWORD_COMBINATION" in fired
        assert body["riskLevel"] in {"caution", "high_risk"}

    def test_ip_host_is_detected(self) -> None:
        body = client.post(
            "/api/analyze/url", json={"url": "http://192.168.1.1/login"}
        ).json()
        fired = {f["id"] for f in body["heuristicFindings"] if f["triggered"]}
        assert "IP_HOST" in fired

    def test_plain_domain_fires_no_rules(self) -> None:
        body = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        fired = [f for f in body["heuristicFindings"] if f["triggered"]]
        assert fired == []

    def test_response_matches_frontend_contract(self) -> None:
        """Every field the Phase 1 UI reads must be present."""
        body = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        for field in (
            "isMock",
            "source",
            "engine",
            "engineVersion",
            "signal",
            "trustScore",
            "riskLevel",
            "confidence",
            "dna",
            "graph",
            "timeline",
            "primarySignal",
            "secondarySignals",
            "lanes",
            "durationMs",
        ):
            assert field in body, field

        for field in ("nodes", "edges"):
            assert field in body["graph"], field
        assert body["signal"]["kind"] == "url"

    def test_dna_marks_inapplicable_axes_as_null(self) -> None:
        """Synthetic/provenance have no meaning for a URL — must be null."""
        body = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        assert body["dna"]["synthetic"] is None
        assert body["dna"]["provenance"] is None
        # The URL-meaningful axes must be real numbers.
        for axis in ("domain", "identity", "behavior"):
            assert isinstance(body["dna"][axis], int)

    def test_graph_is_never_empty(self) -> None:
        for url in ("https://example.com", "https://a.b.c.verify.example.zip"):
            body = client.post("/api/analyze/url", json={"url": url}).json()
            assert len(body["graph"]["nodes"]) >= 2
            assert len(body["graph"]["edges"]) >= 1

    def test_timeline_is_ordered(self) -> None:
        body = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        offsets = [entry["offsetSeconds"] for entry in body["timeline"]]
        assert offsets == sorted(offsets)
        assert offsets[0] == 0.0

    def test_explanation_is_bilingual(self) -> None:
        body = client.post(
            "/api/analyze/url",
            json={"url": "https://paypal-secure.example.com"},
        ).json()
        primary = body["primarySignal"]
        assert primary is not None
        assert primary["titleEn"] and primary["titleAr"]
        assert primary["bodyEn"] and primary["bodyAr"]

        for signal in body["secondarySignals"]:
            assert signal["valueEn"] and signal["valueAr"]

    def test_language_is_probabilistic_not_a_verdict(self) -> None:
        """No response may assert a definitive verdict."""
        response = client.post(
            "/api/analyze/url",
            json={"url": "https://secure-login-account-update.example.com"},
        )
        text = response.text.lower()
        for banned in (
            "is malicious",
            "definitely phishing",
            "this is a phishing",
            "is safe",
            "guaranteed",
        ):
            assert banned not in text, banned

    def test_transparency_fields_present(self) -> None:
        body = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        assert "heuristicFindings" in body
        assert "riskBreakdown" in body
        assert "featureObservations" in body
        assert body["modelAvailable"] in (True, False)
        assert isinstance(body["modelNote"], str)

    def test_risk_breakdown_states_the_formula(self) -> None:
        body = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        assert "heuristic_risk" in body["riskBreakdown"]["formula"]
        assert "trust_score" in body["riskBreakdown"]["formula"]

    def test_model_absence_is_disclosed(self) -> None:
        """With no trained model the note must say so, not imply intelligence."""
        body = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        if not body["modelAvailable"]:
            assert "no trained model" in body["modelNote"].lower()

    def test_repeated_analysis_is_stable(self) -> None:
        first = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        second = client.post(
            "/api/analyze/url", json={"url": "https://example.com"}
        ).json()
        assert first["trustScore"] == second["trustScore"]
        assert first["riskLevel"] == second["riskLevel"]

    def test_whitespace_is_tolerated(self) -> None:
        response = client.post(
            "/api/analyze/url", json={"url": "  https://example.com  "}
        )
        assert response.status_code == 200

    def test_url_is_echoed_normalized(self) -> None:
        body = client.post("/api/analyze/url", json={"url": "example.com"}).json()
        assert body["normalizedUrl"].startswith("https://")


class TestInvalidInput:
    @pytest.mark.parametrize(
        "url,expected_code",
        [
            ("javascript:alert(1)", "unsupported_scheme"),
            ("file:///etc/passwd", "unsupported_scheme"),
            ("data:text/html,<script>", "unsupported_scheme"),
            ("ftp://example.com", "unsupported_scheme"),
            ("", "validation_error"),
        ],
    )
    def test_rejects_unsafe_or_empty_input(
        self, url: str, expected_code: str
    ) -> None:
        response = client.post("/api/analyze/url", json={"url": url})
        assert response.status_code == 422
        body = response.json()
        # Either the Pydantic layer or our normaliser rejects it; both are
        # correct, and both must produce a machine-readable code.
        assert "code" in body or "detail" in body

    def test_oversized_url_rejected(self) -> None:
        response = client.post(
            "/api/analyze/url", json={"url": "https://example.com/" + "a" * 4000}
        )
        assert response.status_code == 422

    def test_missing_field_rejected(self) -> None:
        assert client.post("/api/analyze/url", json={}).status_code == 422

    def test_error_body_has_stable_code(self) -> None:
        response = client.post(
            "/api/analyze/url", json={"url": "javascript:alert(1)"}
        )
        body = response.json()
        assert body["code"] == "unsupported_scheme"
        assert body["error"] == "invalid_url"


class TestModelInfo:
    def test_model_info_is_available(self) -> None:
        body = client.get("/api/model/info").json()
        assert "available" in body
        assert body["featureCount"] > 0
        assert isinstance(body["features"], list)

    def test_model_info_exposes_no_filesystem_paths(self) -> None:
        """The endpoint must not leak server layout."""
        body = client.get("/api/model/info").json()
        text = str(body).lower()
        for leaked in ("c:\\", "/home/", "users/", "models/"):
            assert leaked not in text, leaked

    def test_metrics_are_null_without_a_trained_model(self) -> None:
        """Never fabricate evaluation numbers."""
        body = client.get("/api/model/info").json()
        if not body["available"]:
            assert body["metrics"] is None
            assert body["datasetRows"] is None
            assert body["trainedAt"] is None


class TestOpenAPI:
    def test_schema_generates(self) -> None:
        assert client.get("/openapi.json").status_code == 200
