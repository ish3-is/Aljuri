"""
Unit tests for URL normalization.

These assert STRUCTURAL behaviour only. No test claims that a real domain
is malicious or benign — that judgement belongs to the model and to a
human analyst, not to a fixture file.
"""

from __future__ import annotations

import pytest

from app.services.url_analyzer import InvalidURLError, decode_for_lexical_analysis, normalize


class TestNormalizationAcceptsRealShapes:
    """The forms a person actually types must all work."""

    @pytest.mark.parametrize(
        "raw,expected_scheme",
        [
            ("example.com", "https"),
            ("http://example.com", "http"),
            ("https://example.com", "https"),
            ("http://example.com/login", "http"),
            ("https://example.com/a/b?c=d#e", "https"),
            ("  https://example.com  ", "https"),
        ],
    )
    def test_accepts_typed_shapes(self, raw: str, expected_scheme: str) -> None:
        url = normalize(raw)
        assert url.scheme == expected_scheme
        assert url.hostname == "example.com"

    def test_www_prefix_is_preserved_as_a_subdomain(self) -> None:
        """`www` is a legitimate label and must not be silently stripped."""
        url = normalize("www.example.com")
        assert url.hostname == "www.example.com"
        assert url.subdomain == "www"

    def test_host_is_lowercased(self) -> None:
        assert normalize("https://EXAMPLE.COM/Path").hostname == "example.com"

    def test_missing_scheme_defaults_to_https(self) -> None:
        assert normalize("example.com").uses_https is True

    def test_splits_components(self) -> None:
        url = normalize("https://a.b.example.co.uk:8443/p?q=1#f")
        assert url.hostname == "a.b.example.co.uk"
        assert url.port == 8443
        assert url.registered_domain == "example.co.uk"
        assert url.suffix == "co.uk"
        assert url.subdomain == "a.b"
        assert url.subdomain_depth == 2
        assert url.path == "/p"
        assert url.query == "q=1"
        assert url.fragment == "f"

    def test_original_is_preserved(self) -> None:
        assert normalize("example.com").original == "example.com"


class TestSchemeRejection:
    """Unsafe schemes are refused at the boundary, never normalised."""

    @pytest.mark.parametrize(
        "raw",
        [
            "javascript:alert(1)",
            "file:///etc/passwd",
            "data:text/html,<script>alert(1)</script>",
            "ftp://example.com",
            "vbscript:msgbox(1)",
        ],
    )
    def test_rejects_non_web_schemes(self, raw: str) -> None:
        with pytest.raises(InvalidURLError) as exc:
            normalize(raw)
        assert exc.value.code == "unsupported_scheme"

    def test_rejection_happens_before_parsing(self) -> None:
        """A javascript: payload must never reach urlsplit as a host."""
        with pytest.raises(InvalidURLError):
            normalize("javascript:alert(document.cookie)")


class TestSizeAndEmptiness:
    def test_rejects_empty(self) -> None:
        with pytest.raises(InvalidURLError) as exc:
            normalize("   ")
        assert exc.value.code == "empty_url"

    def test_rejects_oversized(self) -> None:
        with pytest.raises(InvalidURLError) as exc:
            normalize("https://example.com/" + "a" * 4000)
        assert exc.value.code == "url_too_long"

    def test_accepts_url_at_the_limit(self) -> None:
        # Exactly at the boundary should not raise on length alone.
        base = "https://example.com/"
        raw = base + "a" * (2048 - len(base))
        assert len(raw) == 2048
        assert normalize(raw) is not None


class TestHostValidation:
    def test_rejects_missing_host(self) -> None:
        with pytest.raises(InvalidURLError) as exc:
            normalize("https://")
        assert exc.value.code in {"missing_host", "invalid_host"}

    def test_rejects_invalid_port(self) -> None:
        with pytest.raises(InvalidURLError) as exc:
            normalize("https://example.com:notaport/")
        assert exc.value.code == "invalid_port"

    def test_multiple_at_signs_resolve_to_the_final_host(self) -> None:
        """`a@b@host` is userinfo `a@b` with host `host`, per RFC 3986.

        The normalizer must expose exactly that, so the AT_SYMBOL rule
        can observe the embedded credentials rather than the host looking
        innocent.
        """
        url = normalize("https://example.com@evil.com@127.0.0.1")
        assert url.hostname == "127.0.0.1"
        assert url.has_userinfo() is True

    def test_rejects_space_in_host(self) -> None:
        with pytest.raises(InvalidURLError) as exc:
            normalize("https://exa mple.com")
        assert exc.value.code == "invalid_host"

    def test_space_in_path_is_accepted(self) -> None:
        """A space in the path is unusual but not a host violation."""
        assert normalize("https://example.com/a path").hostname == "example.com"


class TestIPDetection:
    def test_detects_ipv4(self) -> None:
        assert normalize("http://192.168.1.1/login").is_ip_host is True

    def test_detects_ipv6(self) -> None:
        assert normalize("http://[2001:db8::1]/").is_ip_host is True

    def test_domain_is_not_ip(self) -> None:
        assert normalize("https://example.com").is_ip_host is False

    def test_ip_has_no_registered_domain(self) -> None:
        url = normalize("http://192.168.1.1/login")
        assert url.registered_domain == "192.168.1.1"


class TestPunycode:
    def test_detects_punycode_label(self) -> None:
        url = normalize("https://xn--example-test.invalid")
        assert url.is_punycode is True

    def test_plain_domain_is_not_punycode(self) -> None:
        assert normalize("https://example.com").is_punycode is False


class TestUserinfo:
    def test_detects_at_symbol_credentials(self) -> None:
        url = normalize("https://user:pass@example.com/login")
        assert url.has_userinfo() is True
        assert url.username == "user"

    def test_no_userinfo(self) -> None:
        assert normalize("https://example.com/login").has_userinfo() is False


class TestInvisibleCharacters:
    def test_strips_zero_width_characters(self) -> None:
        """Zero-width chars must not silently change measured lengths."""
        dirty = "https://exam\u200bple.com"
        url = normalize(dirty)
        assert url.hostname == "example.com"

    def test_strips_bidi_overrides(self) -> None:
        url = normalize("https://example.com/\u202eexe.txt")
        assert "\u202e" not in url.normalized

    def test_strips_null_bytes(self) -> None:
        assert "\x00" not in normalize("https://exa\x00mple.com").normalized


class TestDecoding:
    def test_decodes_percent_encoding(self) -> None:
        assert decode_for_lexical_analysis("%6c%6f%67%69%6e") == "login"

    def test_decoding_empty_string(self) -> None:
        assert decode_for_lexical_analysis("") == ""

    def test_decoding_tolerates_bad_escapes(self) -> None:
        # Must not raise; malformed escapes are left as-is.
        assert isinstance(decode_for_lexical_analysis("%zz%"), str)
