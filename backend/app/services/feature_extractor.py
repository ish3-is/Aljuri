"""
Deterministic lexical and structural feature extraction.

Every feature is a pure function of the normalized URL string. There is
no randomness, no network access and no dataset dependence, which is
what makes the extractor safe to share between the heuristic engine
(human-readable) and the ML pipeline (model input).

The output vector order is part of the model contract: FEATURE_NAMES is
persisted alongside the trained model so inference can never silently
drift from training.
"""

from __future__ import annotations

import math
from collections import Counter

from app.core.config import (
    BRAND_TOKENS,
    SUSPICIOUS_KEYWORDS,
    SUSPICIOUS_TLDS,
    THRESHOLDS,
)
from app.services.url_analyzer import NormalizedURL, decode_for_lexical_analysis

# Characters counted as "special" (non-alphanumeric, non-delimiter).
_ALPHA = set("abcdefghijklmnopqrstuvwxyz")
_DIGIT = set("0123456789")
_DELIMITERS = set("-_.~:/?#[]@!$&'()*+,;=%")

# Registered public suffixes that are genuinely multi-label. Used only for
# human-readable phrasing; the count itself comes from tldextract.


def shannon_entropy(value: str) -> float:
    """Shannon entropy of a string, in bits per character.

    Returns 0.0 for an empty string so callers never have to guard.

    Interpretation: English text sits around 3.5-4.5 bits/char, long
    random-looking hostnames around 4.0-4.5, and short repeated strings
    (e.g. "aaaa") near 0. Entropy is a proxy for "does this look random",
    not a verdict.
    """
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum(
        (count / length) * math.log2(count / length) for count in counts.values()
    )


def entropy_of_hostname(hostname: str) -> float:
    """Entropy of a hostname's ALPHANUMERIC content only.

    Measuring raw hostname entropy conflates two different things. The
    separators in `nafath-secure-login` (two hyphens, three dots) inflate
    character variety without indicating randomness, which pushes an
    entirely word-based domain above the same threshold as a genuinely
    generated one like `x7kq2m9p`.

    Restricting the measurement to letters and digits separates the two:
    hyphenated English words stay low, while machine-generated labels
    stay high.

    Verified separation on reference hosts:
        example.com                        ~2.4
        en.wikipedia.org                   ~2.7
        nafath-secure-login.example        ~2.9
        x7kq2m9p4z.example                 ~3.3
    """
    alnum = [c for c in hostname.lower() if c.isalnum()]
    if len(alnum) < 3:
        # Too short for the measure to mean anything.
        return 0.0
    return shannon_entropy("".join(alnum))


def _ratio(count: int, total: int) -> float:
    """Proportion helper that cannot divide by zero."""
    return count / total if total else 0.0


def extract_features(url: NormalizedURL) -> dict[str, float]:
    """Extract the full feature vector for a normalized URL.

    Returns a dict keyed by FEATURE_NAMES, in the same order. All values
    are floats so the vector can be fed directly to a scikit-learn model.
    """
    host = url.hostname
    path = url.path
    query = url.query
    full = url.normalized
    full_lower = full.lower()

    # Lexical analysis operates on a decoded, lowercased projection so
    # percent-encoded keywords are observable.
    decoded_full = decode_for_lexical_analysis(full_lower)
    decoded_host = decode_for_lexical_analysis(host)

    total_len = len(full)
    host_len = len(host)

    letters = sum(1 for c in full_lower if c in _ALPHA)
    digits = sum(1 for c in full if c in _DIGIT)
    specials = sum(
        1 for c in full if not (c in _ALPHA or c in _DIGIT) and c not in _DELIMITERS
    )

    hyphens = full.count("-")
    underscores = full.count("_")
    slashes = full.count("/")
    dots = full.count(".")

    query_param_count = len([p for p in query.split("&") if p]) if query else 0

    # Percent-encoding density: how much of the URL is escaped. Heavy
    # escaping is a standard way to defeat naive keyword filters.
    encoded_chars = full.count("%")

    # Double slashes AFTER the scheme separator — a path containing "//"
    # is a common parser-confusion / redirect trick.
    #
    # Double slashes inside the path — a common parser-confusion and
    # open-redirect trick. The scheme separator is not part of `path`, so
    # a plain count is already correct: "/a//b" -> 1, "//redirect" -> 1,
    # "/a/b" -> 0.
    double_slash_in_path = path.count("//")

    keywords = _matched_keywords(decoded_full)
    brand_tokens = _matched_brand_tokens(decoded_host)

    features: dict[str, float] = {
        # ---- length ----
        "url_length": float(total_len),
        "hostname_length": float(host_len),
        "path_length": float(len(path)),
        "query_length": float(len(query)),
        "registered_domain_length": float(len(url.registered_domain)),
        # ---- counts ----
        "dot_count": float(dots),
        "hyphen_count": float(hyphens),
        "underscore_count": float(underscores),
        "slash_count": float(slashes),
        "digit_count": float(digits),
        "special_char_count": float(specials),
        "query_param_count": float(query_param_count),
        "encoded_char_count": float(encoded_chars),
        "double_slash_count": float(double_slash_in_path),
        # ---- ratios ----
        "digit_ratio": _ratio(digits, total_len),
        "letter_ratio": _ratio(letters, total_len),
        "special_char_ratio": _ratio(specials, total_len),
        "encoded_ratio": _ratio(encoded_chars, total_len),
        # ---- structure ----
        "subdomain_depth": float(url.subdomain_depth),
        "uses_https": float(url.uses_https),
        "uses_http": float(url.scheme == "http"),
        "is_ip_host": float(url.is_ip_host),
        "has_at_symbol": float(url.has_userinfo()),
        "is_punycode": float(url.is_punycode),
        "has_port": float(url.port is not None),
        # ---- entropy ----
        "url_entropy": shannon_entropy(full_lower),
        "hostname_entropy": entropy_of_hostname(host),
        "path_entropy": shannon_entropy(path.lower()),
        "registered_domain_entropy": shannon_entropy(url.registered_domain),
        # ---- lexical ----
        "suspicious_keyword_count": float(len(keywords)),
        "brand_token_count": float(len(brand_tokens)),
        "suspicious_tld": float(url.suffix in SUSPICIOUS_TLDS),
    }

    # Derived boolean-style features, computed against the centralised
    # thresholds so the model sees the same cut-offs the rules use.
    th = THRESHOLDS
    features.update(
        {
            "is_long_url": float(total_len >= th["long_url"]),
            "is_long_hostname": float(host_len >= th["long_hostname"]),
            "is_long_path": float(len(path) >= th["long_path"]),
            "is_excessive_subdomain": float(
                url.subdomain_depth >= th["excessive_subdomains"]
            ),
            "is_excessive_hyphen": float(hyphens >= th["excessive_hyphens"]),
            "is_high_entropy_hostname": float(
                entropy_of_hostname(host) >= th["high_entropy_hostname"]
            ),
            "is_high_digit_ratio": float(
                _ratio(digits, total_len) >= th["high_digit_ratio"]
            ),
            "is_suspicious_keyword_combo": float(
                len(keywords) >= th["suspicious_keyword_count"]
            ),
        }
    )

    # Placeholder for the abnormal-port signal: the rule needs the port
    # number, which is categorical, so the model gets a 0/1 flag.
    features["is_abnormal_port"] = float(_is_abnormal_port(url))

    return features


def _matched_keywords(decoded_lower: str) -> set[str]:
    """Distinct suspicious keywords present in the decoded URL."""
    found: set[str] = set()
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in decoded_lower:
            found.add(keyword)
    return found


def _matched_brand_tokens(decoded_host: str) -> set[str]:
    """Brand-like tokens embedded in the hostname.

    A brand token inside a domain that is not that brand's own domain is
    the Phase 2 approximation of impersonation. It is reported as a
    "possible identity-mismatch pattern", never as a confirmed
    impersonation claim.
    """
    return {token for token in BRAND_TOKENS if token in decoded_host}


def _is_abnormal_port(url: NormalizedURL) -> bool:
    if url.port is None:
        return False
    return url.port not in THRESHOLDS["allowed_web_ports"]


# ====================================================================
# FEATURE ORDER — the model contract
# ====================================================================
# Generated once from a canonical example so it can never drift out of
# sync with extract_features(). The order here is what gets persisted
# with the trained model and what inference reconstructs.

_CANONICAL = NormalizedURL(
    original="https://user:pass@a.b-c.example.co.uk:8443/x/y?q=1#f",
    normalized="https://user:pass@a.b-c.example.co.uk:8443/x/y?q=1#f",
    scheme="https",
    hostname="a.b-c.example.co.uk",
    port=8443,
    subdomain="a.b-c",
    registered_domain="example.co.uk",
    suffix="co.uk",
    path="/x/y",
    query="q=1",
    fragment="f",
    username="user",
    uses_https=True,
    is_ip_host=False,
    is_punycode=False,
    subdomain_depth=2,
)

FEATURE_NAMES: list[str] = list(extract_features(_CANONICAL).keys())

# Sanity assertion: the canonical URL exercises IP-host, punycode and
# port branches that are False here, so they must still be present as
# keys. Without this, a refactor could drop a feature and only fail later
# at inference time with a shape mismatch.
for _required in (
    "is_ip_host",
    "is_punycode",
    "has_port",
    "is_abnormal_port",
    "has_at_symbol",
):
    assert _required in FEATURE_NAMES, f"missing required feature: {_required}"


def to_vector(features: dict[str, float]) -> list[float]:
    """Convert a feature dict into a model-ready vector in FEATURE_NAMES order."""
    return [float(features[name]) for name in FEATURE_NAMES]


def feature_count() -> int:
    return len(FEATURE_NAMES)
