"""
URL normalization and validation.

This module is the security boundary of the backend. A submitted URL is
treated as an untrusted string: it is parsed, never dereferenced.

Explicit non-goals, by design (Phase 2 scope):
  * the URL is never opened, navigated to, or requested
  * no DNS resolution is performed
  * no page content is downloaded
  * no JavaScript is executed

Everything here operates on the string the user typed.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

import tldextract

from app.core.config import settings

# tldextract is configured offline. By default it fetches the public suffix
# list over the network on first use and caches it, which would make
# analysis non-reproducible and would leak a request per cold start.
# `suffix_list_urls=()` forces use of the snapshot bundled with the
# package — deterministic, offline, and identical across environments.
_EXTRACT = tldextract.TLDExtract(
    suffix_list_urls=(),
    fallback_to_snapshot=True,
)

# A scheme we are willing to reason about. Matched before parsing so a
# `javascript:` or `file:` payload is rejected rather than normalised.
_SCHEME_RE = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9+.\-]*)\s*:")
# C0/C1 control characters, DEL, zero-width and bidi-override characters.
# Written as explicit escapes because a literal U+200F directly after a
# hex escape would be parsed as the upper bound of a character range.
_INVISIBLE_RE = re.compile(
    "[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]"
)
# Characters that have no legitimate place in a hostname.
#
# Square brackets are deliberately excluded: they delimit a legal IPv6
# literal, which urlsplit hands back with the brackets already stripped.
# The class is built by concatenation because an escaped closing bracket
# inside a raw string is easy to get subtly wrong.
_HOST_ILLEGAL = re.compile("[\\s\\\\@#?/\\]]")
_PUNYCODE_RE = re.compile(r"^xn--", re.IGNORECASE)
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


class InvalidURLError(ValueError):
    """Raised when a submitted string cannot be treated as a URL.

    Carries a stable machine-readable `code` so the API layer can map it
    to an HTTP status without string matching.
    """

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class NormalizedURL:
    """A URL broken into the parts the feature extractor reasons about."""

    original: str
    """Exactly what the user submitted."""

    normalized: str
    """Canonical form used for all downstream analysis."""

    scheme: str
    hostname: str
    """Lowercased host. Empty for IP-literal hosts."""

    port: int | None

    subdomain: str
    registered_domain: str
    """Second-level name plus public suffix, e.g. `example.co.uk`."""

    suffix: str
    """Public suffix, e.g. `co.uk`. Empty when unparseable."""

    path: str
    query: str
    fragment: str

    username: str
    """Userinfo before '@'. Its presence is itself a strong signal."""

    uses_https: bool
    is_ip_host: bool
    is_punycode: bool
    subdomain_depth: int
    """Number of labels in the subdomain, excluding the registered domain."""

    def has_userinfo(self) -> bool:
        return bool(self.username)


def _looks_like_ipv4(host: str) -> bool:
    if not _IPV4_RE.match(host):
        return False
    try:
        ipaddress.IPv4Address(host)
        return True
    except ipaddress.AddressValueError:
        return False


def _looks_like_ipv6(host: str) -> bool:
    candidate = host.strip("[]")
    try:
        ipaddress.IPv6Address(candidate)
        return True
    except ipaddress.AddressValueError:
        return False


def normalize(raw: str) -> NormalizedURL:
    """Validate and decompose a submitted URL.

    Accepts the shapes a person actually types: `example.com`,
    `www.example.com/login`, `https://example.com/a?b=c`.

    Raises InvalidURLError for anything that is empty, oversized, uses a
    scheme outside the allow-list, or cannot be decomposed into a host.
    """
    if raw is None:
        raise InvalidURLError("No URL was provided.", "empty_url")

    # Strip control characters and zero-width marks. These are invisible
    # but change string length, token matching and feature values, so
    # they must be removed before anything is measured.
    cleaned = _INVISIBLE_RE.sub("", raw).strip()

    if not cleaned:
        raise InvalidURLError("No URL was provided.", "empty_url")

    if len(cleaned) > settings.max_url_length:
        raise InvalidURLError(
            f"URL exceeds the maximum supported length of "
            f"{settings.max_url_length} characters.",
            "url_too_long",
        )

    # --- scheme gate -------------------------------------------------
    scheme_match = _SCHEME_RE.match(cleaned)
    if scheme_match:
        scheme = scheme_match.group(1).lower()
        if scheme not in settings.allowed_schemes:
            raise InvalidURLError(
                f"Scheme '{scheme}' is not supported. Only "
                f"{', '.join(sorted(settings.allowed_schemes))} are analysed.",
                "unsupported_scheme",
            )
    else:
        # No scheme: default to https, which is the least assuming.
        scheme = "https"

    # urlsplit does not enforce the scheme, so we prepend the default
    # rather than relying on the user's text.
    candidate = cleaned if scheme_match else f"{scheme}://{cleaned}"

    try:
        parts = urlsplit(candidate)
    except ValueError as exc:
        raise InvalidURLError(f"URL could not be parsed: {exc}", "unparsable") from exc

    # --- host --------------------------------------------------------
    # `hostname` lowercases and strips brackets/port/userinfo for us.
    try:
        hostname = (parts.hostname or "").lower()
    except ValueError as exc:
        raise InvalidURLError(f"URL host is invalid: {exc}", "invalid_host") from exc

    if not hostname:
        raise InvalidURLError("URL does not contain a hostname.", "missing_host")

    # Reject hosts containing characters that cannot occur in a hostname.
    # '@' inside the host portion means a userinfo-splitting trick.
    #
    # `parts.netloc` still carries the brackets around an IPv6 literal
    # even though `parts.hostname` strips them, so a bracketed literal is
    # validated as a literal rather than run through the host-character
    # rules that `[` and `]` would (correctly) trip.
    host_portion = parts.netloc.split("@")[-1]
    if not (
        host_portion.startswith("[") and host_portion.endswith("]")
    ) and _HOST_ILLEGAL.search(host_portion):
        raise InvalidURLError(
            "URL hostname contains characters that are not valid in a host.",
            "invalid_host",
        )

    port: int | None = None
    try:
        port = parts.port
    except ValueError as exc:
        # urlsplit raises for a non-numeric or out-of-range port.
        raise InvalidURLError(f"URL port is invalid: {exc}", "invalid_port") from exc

    is_ip_host = _looks_like_ipv4(hostname) or _looks_like_ipv6(hostname)

    # --- registered domain ------------------------------------------
    # An IP host has no registrable domain, so the decomposition is
    # skipped rather than guessed at.
    if is_ip_host:
        subdomain, registered_domain, suffix = "", hostname, ""
    else:
        extracted = _EXTRACT(hostname)
        registered_domain = extracted.registered_domain.lower()
        suffix = extracted.suffix.lower()
        subdomain = extracted.subdomain.lower()

    subdomain_depth = (
        len([label for label in subdomain.split(".") if label]) if subdomain else 0
    )

    path = parts.path or ""
    query = parts.query or ""
    fragment = parts.fragment or ""
    username = parts.username or ""

    is_punycode = bool(_PUNYCODE_RE.search(hostname)) or bool(
        _PUNYCODE_RE.search(registered_domain)
    )

    return NormalizedURL(
        original=raw,
        normalized=candidate,
        scheme=scheme,
        hostname=hostname,
        port=port,
        subdomain=subdomain,
        registered_domain=registered_domain,
        suffix=suffix,
        path=path,
        query=query,
        fragment=fragment,
        username=username,
        uses_https=(scheme == "https"),
        is_ip_host=is_ip_host,
        is_punycode=is_punycode,
        subdomain_depth=subdomain_depth,
    )


def decode_for_lexical_analysis(value: str) -> str:
    """Percent-decode a string so obfuscated keywords become visible.

    Only used for lexical inspection. A URL containing `%6c%6f%67%69%6e`
    is trying to hide the word "login" from a naive reader; decoding it
    locally is how we observe that, without fetching anything.
    """
    try:
        return unquote(value, errors="replace")
    except Exception:
        return value
