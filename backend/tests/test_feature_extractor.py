"""
Unit tests for feature extraction and entropy.

The feature vector is the model contract, so its stability is tested
explicitly: a refactor that silently adds, drops or reorders a feature
would break a trained model at inference time.
"""

from __future__ import annotations

import math

import pytest

from app.services.feature_extractor import (
    FEATURE_NAMES,
    extract_features,
    shannon_entropy,
    to_vector,
)
from app.services.url_analyzer import normalize


class TestEntropy:
    def test_empty_string_is_zero(self) -> None:
        assert shannon_entropy("") == 0.0

    def test_uniform_string_is_zero(self) -> None:
        assert shannon_entropy("aaaa") == 0.0

    def test_maximum_for_two_equally_likely_chars(self) -> None:
        assert shannon_entropy("ab") == 1.0

    def test_known_value(self) -> None:
        # "aab": p(a)=2/3, p(b)=1/3
        expected = -(2 / 3) * math.log2(2 / 3) - (1 / 3) * math.log2(1 / 3)
        assert shannon_entropy("aab") == pytest.approx(expected, abs=1e-9)

    def test_english_like_string_is_mid_range(self) -> None:
        value = shannon_entropy("login")
        assert 1.5 < value < 3.5

    def test_random_looking_is_higher_than_word(self) -> None:
        assert shannon_entropy("x7kq2m9p") > shannon_entropy("login")



class TestFeatureContract:
    """The feature vector is persisted with the model; it must not drift."""

    def test_feature_names_are_unique(self) -> None:
        assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))

    def test_feature_count_is_substantial(self) -> None:
        assert len(FEATURE_NAMES) >= 40

    def test_required_features_present(self) -> None:
        for name in (
            "url_length",
            "hostname_length",
            "digit_ratio",
            "is_ip_host",
            "is_punycode",
            "has_at_symbol",
            "url_entropy",
            "hostname_entropy",
            "subdomain_depth",
            "uses_https",
            "suspicious_keyword_count",
        ):
            assert name in FEATURE_NAMES, name

    def test_vector_length_matches_names(self) -> None:
        features = extract_features(normalize("https://example.com"))
        assert len(to_vector(features)) == len(FEATURE_NAMES)

    def test_vector_order_follows_names(self) -> None:
        url = normalize("https://example.com")
        features = extract_features(url)
        vector = to_vector(features)
        assert vector[FEATURE_NAMES.index("url_length")] == features["url_length"]

    def test_features_are_deterministic(self) -> None:
        """Same input, same output — required for reproducible analysis."""
        url = normalize("https://secure-login-account-update.example.com")
        assert extract_features(url) == extract_features(url)

    def test_all_values_are_finite_numbers(self) -> None:
        url = normalize("http://192.168.1.1:8080/a/b?c=d")
        for name, value in extract_features(url).items():
            assert isinstance(value, float), name
            assert not math.isnan(value), name
            assert not math.isinf(value), name


class TestLexicalFeatures:
    def test_lengths(self) -> None:
        f = extract_features(normalize("https://example.com/some/path"))
        assert f["hostname_length"] == 11.0
        assert f["path_length"] == len("/some/path")

    def test_digit_ratio(self) -> None:
        f = extract_features(normalize("https://example123.com"))
        assert f["digit_ratio"] > 0
        assert f["digit_ratio"] < 1

    def test_punycode_feature_set(self) -> None:
        f = extract_features(normalize("https://xn--example-test.invalid"))
        assert f["is_punycode"] == 1.0

    def test_ip_host_feature(self) -> None:
        f = extract_features(normalize("http://192.168.1.1/login"))
        assert f["is_ip_host"] == 1.0

    def test_at_symbol_feature(self) -> None:
        f = extract_features(normalize("https://user@example.com"))
        assert f["has_at_symbol"] == 1.0

    def test_https_feature(self) -> None:
        assert extract_features(normalize("https://example.com"))["uses_https"] == 1.0
        assert extract_features(normalize("http://example.com"))["uses_http"] == 1.0

    def test_subdomain_depth(self) -> None:
        f = extract_features(normalize("https://a.b.c.example.com"))
        assert f["subdomain_depth"] == 3.0

    def test_query_param_count(self) -> None:
        f = extract_features(normalize("https://example.com/?a=1&b=2&c=3"))
        assert f["query_param_count"] == 3.0

    def test_encoded_chars_detected(self) -> None:
        f = extract_features(normalize("https://example.com/%6c%6f%67%69%6e"))
        assert f["encoded_char_count"] > 0
        assert f["encoded_ratio"] > 0

    def test_double_slash_in_path(self) -> None:
        f = extract_features(normalize("https://example.com//redirect"))
        assert f["double_slash_count"] >= 1.0

    def test_abnormal_port(self) -> None:
        assert extract_features(normalize("https://example.com:9999/"))["is_abnormal_port"] == 1.0
        assert extract_features(normalize("https://example.com:443/"))["is_abnormal_port"] == 0.0


class TestKeywordFeatures:
    def test_single_keyword_does_not_trigger_combination(self) -> None:
        """A lone 'login' is unremarkable and must not fire the combo rule."""
        f = extract_features(normalize("https://example.com/login"))
        assert f["suspicious_keyword_count"] == 1.0
        assert f["is_suspicious_keyword_combo"] == 0.0

    def test_multiple_keywords_trigger_combination(self) -> None:
        f = extract_features(
            normalize("https://example.com/login/verify/account-update")
        )
        assert f["suspicious_keyword_count"] >= 3.0
        assert f["is_suspicious_keyword_combo"] == 1.0

    def test_percent_encoded_keyword_is_visible_after_decoding(self) -> None:
        """%6c%6f%67%69%6e is 'login' — encoding must not hide it."""
        f = extract_features(normalize("https://example.com/%6c%6f%67%69%6e"))
        assert f["suspicious_keyword_count"] >= 1.0

    def test_brand_token_detected(self) -> None:
        f = extract_features(normalize("https://paypal-secure.example.com"))
        assert f["brand_token_count"] >= 1.0

    def test_no_keywords_on_plain_domain(self) -> None:
        f = extract_features(normalize("https://example.com"))
        assert f["suspicious_keyword_count"] == 0.0
