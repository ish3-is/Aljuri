"""
Explainable heuristic engine.

Each rule is a small, independently testable predicate that returns a
HeuristicFinding. A rule answers only about observable structure of the
submitted URL string — never about whether the site is "really"
malicious.

Design rule that matters academically: NO SINGLE RULE can classify a URL
as high risk on its own. The risk engine enforces that structurally, and
this module never emits a verdict.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from inspect import signature
from typing import Callable

from app.core.config import (
    BRAND_TOKENS,
    HEURISTIC_WEIGHTS,
    SUSPICIOUS_KEYWORDS,
    SUSPICIOUS_TLDS,
    THRESHOLDS,
)
from app.services.feature_extractor import (
    entropy_of_hostname,
    extract_features,
    shannon_entropy,
    to_vector,
)
from app.services.url_analyzer import NormalizedURL, decode_for_lexical_analysis

Severity = str  # "high" | "medium" | "low"


@dataclass(frozen=True)
class HeuristicFinding:
    """One explainable observation about the URL."""

    id: str
    """Stable rule identifier, e.g. IP_HOST."""

    title: str
    severity: Severity
    weight: int
    """Risk points contributed, from HEURISTIC_WEIGHTS."""

    triggered: bool
    explanation: str
    """Human-readable, probabilistic phrasing. Never a verdict."""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _finding(
    rule_id: str,
    title: str,
    severity: Severity,
    explanation: str,
    triggered: bool,
) -> HeuristicFinding:
    return HeuristicFinding(
        id=rule_id,
        title=title,
        severity=severity if triggered else "low",
        weight=HEURISTIC_WEIGHTS[rule_id] if triggered else 0,
        triggered=triggered,
        explanation=explanation if triggered else "Not observed.",
    )


# ====================================================================
# RULES
# Each returns a HeuristicFinding; the finding is included in the
# response either way (triggered or not) so a defense can show what was
# checked, not only what fired.
# ====================================================================


def rule_ip_host(url: NormalizedURL) -> HeuristicFinding:
    return _finding(
        "IP_HOST",
        "IP address used as hostname",
        "high",
        "The URL uses a raw IP address instead of a registered domain "
        "name, so the destination cannot be attributed to an organisation.",
        url.is_ip_host,
    )


def rule_at_symbol(url: NormalizedURL) -> HeuristicFinding:
    return _finding(
        "AT_SYMBOL",
        "Embedded credentials in URL",
        "high",
        "The URL contains an '@' before the host, which makes the text "
        "to the left of it a username. Legitimate services rarely require "
        "credentials to be typed into the address bar.",
        url.has_userinfo(),
    )


def rule_punycode(url: NormalizedURL) -> HeuristicFinding:
    return _finding(
        "PUNYCODE",
        "Punycode-encoded hostname",
        "high",
        "The hostname uses Punycode ('xn--'), an encoding used to render "
        "non-ASCII characters. It is legitimate for internationalised "
        "domains but is also used to visually imitate another domain.",
        url.is_punycode,
    )


def rule_excessive_encoding(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    ratio = features["encoded_ratio"]
    return _finding(
        "EXCESSIVE_ENCODING",
        "Heavy percent-encoding",
        "medium",
        f"About {ratio:.0%} of the URL is percent-encoded. Dense encoding "
        "is sometimes used to obscure keywords from simple filters.",
        ratio >= THRESHOLDS["excessive_encoding_ratio"],
    )


def rule_abnormal_port(url: NormalizedURL) -> HeuristicFinding:
    abnormal = url.port is not None and url.port not in THRESHOLDS["allowed_web_ports"]
    return _finding(
        "ABNORMAL_PORT",
        "Non-standard port",
        "medium",
        f"The URL targets port {url.port}, which is not a common web port "
        "(80, 443, 8080, 8443). This is legal but uncommon for public "
        "services.",
        abnormal,
    )


def rule_double_slash(url: NormalizedURL) -> HeuristicFinding:
    count = url.path.lstrip("/").count("//")
    return _finding(
        "DOUBLE_SLASH",
        "Repeated slash in path",
        "low",
        f"The path contains {count} occurrence(s) of '//', a pattern "
        "sometimes used to confuse URL parsers about the real destination.",
        count >= THRESHOLDS["double_slash_count"],
    )


def rule_long_url(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    length = features["url_length"]
    return _finding(
        "LONG_URL",
        "Unusually long URL",
        "medium",
        f"The URL is {int(length)} characters long, beyond the "
        f"{int(THRESHOLDS['long_url'])}-character threshold at which URLs "
        "begin to carry hidden content rather than a plain location.",
        length >= THRESHOLDS["long_url"],
    )


def rule_long_hostname(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    length = features["hostname_length"]
    return _finding(
        "LONG_HOSTNAME",
        "Unusually long hostname",
        "medium",
        f"The hostname is {int(length)} characters long, unusually long "
        "for a real organisation's domain.",
        length >= THRESHOLDS["long_hostname"],
    )


def rule_long_path(url: NormalizedURL, features: dict[str, float]) -> HeuristicFinding:
    length = features["path_length"]
    return _finding(
        "LONG_PATH",
        "Unusually long path",
        "low",
        f"The path segment is {int(length)} characters long, which can "
        "indicate an encoded payload placed in the path.",
        length >= THRESHOLDS["long_path"],
    )


def rule_excessive_subdomains(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    depth = url.subdomain_depth
    return _finding(
        "EXCESSIVE_SUBDOMAINS",
        "Deep subdomain nesting",
        "medium",
        f"The hostname has {depth} subdomain levels before the registered "
        f"domain, exceeding the threshold of "
        f"{int(THRESHOLDS['excessive_subdomains'])}. Depth is used to "
        "push the real domain out of view.",
        depth >= THRESHOLDS["excessive_subdomains"],
    )


def rule_high_entropy_hostname(url: NormalizedURL) -> HeuristicFinding:
    entropy = entropy_of_hostname(url.hostname)
    return _finding(
        "HIGH_ENTROPY_HOSTNAME",
        "High-entropy hostname",
        "medium",
        f"The hostname has a character entropy of {entropy:.2f} bits per "
        f"character (threshold {THRESHOLDS['high_entropy_hostname']}). "
        "Machine-generated hostnames tend to look random, while real "
        "organisation names are more structured.",
        entropy >= THRESHOLDS["high_entropy_hostname"],
    )


def rule_high_entropy_url(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    entropy = features["url_entropy"]
    return _finding(
        "HIGH_ENTROPY_URL",
        "High-entropy URL",
        "low",
        f"The whole URL has an entropy of {entropy:.2f} bits per character, "
        "suggesting randomly generated content.",
        entropy >= THRESHOLDS["high_entropy_url"],
    )


def rule_high_digit_ratio(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    ratio = features["digit_ratio"]
    return _finding(
        "HIGH_DIGIT_RATIO",
        "High proportion of digits",
        "medium",
        f"Digits make up {ratio:.0%} of the URL. Organisation domains are "
        "normally word-based; heavy digit use suggests a generated or "
        "parked identifier.",
        ratio >= THRESHOLDS["high_digit_ratio"],
    )


def rule_excessive_hyphens(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    count = features["hyphen_count"]
    return _finding(
        "EXCESSIVE_HYPHENS",
        "Heavily hyphenated URL",
        "low",
        f"The URL contains {int(count)} hyphens. Stacking words with "
        "hyphens is a common way to read as a familiar phrase while "
        "remaining a different domain.",
        count >= THRESHOLDS["excessive_hyphens"],
    )


def rule_suspicious_keyword_combination(
    url: NormalizedURL, features: dict[str, float]
) -> HeuristicFinding:
    decoded = decode_for_lexical_analysis(url.normalized.lower())
    matches = sorted({kw for kw in SUSPICIOUS_KEYWORDS if kw in decoded})
    count = len(matches)
    triggered = count >= THRESHOLDS["suspicious_keyword_count"]
    preview = ", ".join(matches[:4]) if matches else ""
    return _finding(
        "SUSPICIOUS_KEYWORD_COMBINATION",
        "Credential-themed terms combined",
        "medium",
        f"{count} account-verification terms appear in the URL "
        f"({preview}). A single term such as 'login' is unremarkable; the "
        "combination is what is informative."
        if triggered
        else "No combination of credential-themed terms was observed.",
        triggered,
    )


def rule_brand_like_token(url: NormalizedURL) -> HeuristicFinding:
    """Phase 2 impersonation approximation.

    Reports a POSSIBLE identity-mismatch pattern, never a confirmed
    impersonation claim — attributing intent would require inspecting
    page content, which Phase 2 deliberately does not do.
    """
    decoded_host = decode_for_lexical_analysis(url.hostname)
    tokens = sorted({t for t in BRAND_TOKENS if t in decoded_host})

    if not tokens:
        return _finding(
            "BRAND_LIKE_TOKEN",
            "Possible identity-mismatch pattern",
            "low",
            "No organisation-like token was detected in the hostname.",
            False,
        )

    # Reduce the false-positive rate for domains that legitimately
    # contain the token. The token must be a label of the registered
    # domain itself for this to apply — e.g. "paypal.com" or
    # "bank-alrajhi.com". A token appearing only in the SUBDOMAIN
    # ("paypal-secure.example.com") is exactly the mismatch pattern we
    # are looking for, because the serving domain is example.com.
    token = tokens[0]
    registered_labels = url.registered_domain.split(".")
    is_likely_own_domain = token in registered_labels
    triggered = not is_likely_own_domain

    return _finding(
        "BRAND_LIKE_TOKEN",
        "Possible identity-mismatch pattern",
        "medium",
        f"The hostname contains the term '{token}', but the domain "
        f"that actually serves the request is "
        f"'{url.registered_domain or url.hostname}'. This is a pattern "
        "consistent with imitating an organisation, though the URL alone "
        "cannot establish intent."
        if triggered
        else f"The hostname contains '{token}' as a label of its own "
        f"registered domain '{url.registered_domain}', which is consistent "
        "with a legitimate address.",
        triggered,
    )


def rule_suspicious_tld(url: NormalizedURL) -> HeuristicFinding:
    return _finding(
        "SUSPICIOUS_TLD",
        "Top-level domain frequently abused",
        "low",
        f"The suffix '.{url.suffix}' is disproportionately used for "
        "short-lived abuse. This is a weak prior on its own and should be "
        "read alongside other signals.",
        url.suffix in SUSPICIOUS_TLDS,
    )


def rule_credential_in_url(url: NormalizedURL) -> HeuristicFinding:
    """Credentials literally embedded in the authority or query."""
    authority = url.normalized.split("//")[-1].split("/")[0].lower()
    lowered_query = url.query.lower()
    has_inline = url.has_userinfo() or url.username != ""
    has_query_creds = any(
        marker in lowered_query
        for marker in ("password=", "passwd=", "token=", "api_key=", "apikey=")
    )
    triggered = has_inline or has_query_creds
    return _finding(
        "CREDENTIAL_IN_URL",
        "Credentials carried in the URL",
        "high",
        "The URL carries credential material directly in its text. Any "
        "link shared this way leaks the secret to whoever receives it.",
        triggered,
    )


# Rule registry. Adding a rule here is sufficient — the engine, the API
# response and the tests all iterate this tuple.
RULES = (
    rule_ip_host,
    rule_at_symbol,
    rule_punycode,
    rule_credential_in_url,
    rule_excessive_encoding,
    rule_abnormal_port,
    rule_double_slash,
    rule_long_url,
    rule_long_hostname,
    rule_long_path,
    rule_excessive_subdomains,
    rule_high_entropy_hostname,
    rule_high_entropy_url,
    rule_high_digit_ratio,
    rule_excessive_hyphens,
    rule_suspicious_keyword_combination,
    rule_brand_like_token,
    rule_suspicious_tld,
)


def evaluate(url: NormalizedURL) -> list[HeuristicFinding]:
    """Run every rule and return all findings, triggered or not.

    Rules take either (url) or (url, features). The arity is resolved
    from the signature rather than by catching TypeError, because a
    TypeError raised inside a rule body would otherwise be misread as an
    arity mismatch and silently call the rule the wrong way.
    """
    features = extract_features(url)
    findings: list[HeuristicFinding] = []
    for rule in RULES:
        if _takes_features(rule):
            findings.append(rule(url, features))  # type: ignore[call-arg]
        else:
            findings.append(rule(url))  # type: ignore[call-arg]
    return findings


@lru_cache(maxsize=None)
def _takes_features(rule: Callable[..., HeuristicFinding]) -> bool:
    """Whether a rule expects the precomputed feature dict."""
    params = [
        p
        for p in signature(rule).parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    return len(params) >= 2


def triggered(findings: list[HeuristicFinding]) -> list[HeuristicFinding]:
    return [f for f in findings if f.triggered]


def heuristic_risk(findings: list[HeuristicFinding]) -> tuple[float, list[HeuristicFinding]]:
    """Aggregate rule weights into a 0-100 heuristic risk score.

    Sums the weights of triggered rules and saturates at the configured
    ceiling, so stacking many weak rules cannot exceed 100.

    Two EVIDENCE FLOORS are then applied, because the raw sum alone can
    misrepresent the evidence:

    * any high-severity rule lifts the score to CAUTION;
    * two or more independent rules lift the score to CAUTION.

    Without the second floor a URL with genuinely corroborating evidence
    can be reported as "trusted" purely because its weights happened to
    sum a couple of points under the threshold. That is an accident of
    arithmetic being presented as a judgement.

    Both floors are set AT the caution boundary, so they can lift a score
    into CAUTION but never into HIGH RISK. The central safety property —
    that no single rule can convict — is preserved, and reaching high
    risk still requires substantial corroboration.
    """
    from app.core.config import settings

    fired = triggered(findings)
    raw = sum(f.weight for f in fired)
    score = min(100.0, raw / settings.heuristic_saturation * 100.0)

    has_high_severity = any(f.severity == "high" for f in fired)
    has_corroboration = len(fired) >= settings.min_corroborating_rules

    if has_high_severity:
        score = max(score, settings.min_high_severity_score)
    if has_corroboration:
        score = max(score, settings.min_corroborating_score)

    return score, fired


def findings_to_vectors(url: NormalizedURL) -> list[float]:
    """Convenience for callers that need the model vector."""
    return to_vector(extract_features(url))
