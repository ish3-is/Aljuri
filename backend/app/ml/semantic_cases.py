"""
Semantic regression suite.

NOT a benchmark. This is a hand-built set of real, well-known URL
STRUCTURES, used to assert that the model means what it claims.

It exists because corpus metrics cannot detect this class of failure. A
model can report excellent accuracy on a corpus and still flag
`github.com/anthropics` as phishing, because the corpus simply does not
contain that shape. Phase 2B produced exactly that model.

Each entry declares the EXPECTED classification, so a regression is a
specific assertion rather than a vague quality score:

    LEGITIMATE  well-known real services
    PHISHING    structurally blatant impersonation

The phishing entries are deliberately obvious on purpose. This suite is
not measuring detection power; it is measuring whether the model still
knows the difference between a documentation URL and a credential
harvest. A model that fails these is not usable regardless of its AUC.

Every URL here is a real, publicly known host or an RFC-reserved
example domain. Nothing is fetched; these are strings only.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ml.datasets import LEGITIMATE, PHISHING


@dataclass(frozen=True)
class SemanticCase:
    url: str
    expected_label: int
    category: str
    rationale: str


# ====================================================================
# LEGITIMATE — real services, real URL shapes
# ====================================================================

LEGITIMATE_CASES: list[SemanticCase] = [
    # Documentation and reference. These carry deep, multi-segment paths
    # and are exactly what the PhiUSIIL-trained model misclassified.
    SemanticCase(
        "https://docs.python.org/3/library/asyncio.html", LEGITIMATE,
        "documentation", "deep multi-segment documentation path",
    ),
    SemanticCase(
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript", LEGITIMATE,
        "documentation", "localised documentation path",
    ),
    SemanticCase(
        "https://docs.python.org/3/library/asyncio-task.html#tasks", LEGITIMATE,
        "documentation", "path plus fragment",
    ),
    # Repository URLs. '/' separates org from repo, which superficially
    # resembles a path and triggered false positives.
    SemanticCase(
        "https://github.com/anthropics", LEGITIMATE,
        "repository", "organisation page with a single path segment",
    ),
    SemanticCase(
        "https://github.com/anthropics/claude-code", LEGITIMATE,
        "repository", "organisation/repository pair",
    ),
    SemanticCase(
        "https://gitlab.com/group/subgroup/project", LEGITIMATE,
        "repository", "deeply nested repository path",
    ),
    SemanticCase(
        "https://github.com/torvalds/linux/blob/master/README", LEGITIMATE,
        "repository", "repository plus file path",
    ),
    # Encyclopaedic and academic. Article titles contain hyphens and
    # underscores, which resemble phishing keyword stacking.
    SemanticCase(
        "https://en.wikipedia.org/wiki/Main_Page", LEGITIMATE,
        "encyclopedia", "wiki article path",
    ),
    SemanticCase(
        "https://en.wikipedia.org/wiki/Machine_learning", LEGITIMATE,
        "encyclopedia", "underscored article title",
    ),
    SemanticCase(
        "https://arxiv.org/abs/2301.00001", LEGITIMATE,
        "academic", "numeric identifier path",
    ),
    SemanticCase(
        "https://arxiv.org/pdf/2301.00001v2", LEGITIMATE,
        "academic", "versioned PDF path",
    ),
    # Institutional. University sites have deep paths and heavy
    # parameters, and are the audience for this project.
    SemanticCase(
        "https://www.university.edu.sa/", LEGITIMATE,
        "university", "institutional root",
    ),
    SemanticCase(
        "https://portal.university.edu.sa/student/registration", LEGITIMATE,
        "university", "legitimate student portal with a login-like path",
    ),
    SemanticCase(
        "https://www.university.edu.sa/en/admissions/apply", LEGITIMATE,
        "university", "multi-language institutional path",
    ),
    # Query-heavy legitimate services.
    SemanticCase(
        "https://stackoverflow.com/questions/1", LEGITIMATE,
        "qanda", "numeric question id",
    ),
    SemanticCase(
        "https://www.google.com/search?q=phishing+detection", LEGITIMATE,
        "search", "search query parameters",
    ),
    SemanticCase(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", LEGITIMATE,
        "media", "video identifier parameter",
    ),
    # Long but entirely benign.
    SemanticCase(
        "https://www.coursera.org/learn/machine-learning-supervised", LEGITIMATE,
        "education", "long hyphenated course slug",
    ),
    SemanticCase(
        "https://openai.com/research/index", LEGITIMATE,
        "corporate", "corporate research path",
    ),
    SemanticCase(
        "https://www.nasa.gov/mission/mars-2020/perseverance", LEGITIMATE,
        "government", "deep institutional mission path",
    ),
    SemanticCase(
        "https://news.ycombinator.com/item?id=1", LEGITIMATE,
        "news", "news item with numeric parameter",
    ),
    # Non-https is common on older legitimate sites and must not by
    # itself imply phishing.
    SemanticCase(
        "http://www.example.org/index.html", LEGITIMATE,
        "legacy", "plain-http legacy site with a path",
    ),
    SemanticCase(
        "http://neverssl.com/", LEGITIMATE,
        "legacy", "plain-http bare domain",
    ),
]


# ====================================================================
# PHISHING — structurally blatant, on purpose
# ====================================================================

PHISHING_CASES: list[SemanticCase] = [
    SemanticCase(
        "https://secure-login-account-update.example.com", PHISHING,
        "brand-impersonation", "brand token plus credential verbs stacked in hostname",
    ),
    SemanticCase(
        "https://verify-account-billing-now.example.net/reset", PHISHING,
        "brand-impersonation", "credential verbs plus action verb in path",
    ),
    SemanticCase(
        "https://paypal-secure-confirm-login.example.org/webscr", PHISHING,
        "brand-impersonation", "brand plus three credential words",
    ),
    SemanticCase(
        "https://your-account-has-been-suspended.example.com/login", PHISHING,
        "social-engineering", "threatening language plus credential path",
    ),
    SemanticCase(
        "https://appleid.apple.com.login-verify.example.net", PHISHING,
        "subdomain-trick", "brand name used as a subdomain",
    ),
    SemanticCase(
        "https://microsoft-support-alert.example.com/account/restore", PHISHING,
        "brand-impersonation", "brand plus support pretext",
    ),
    # Credential harvesting against a bare IP.
    SemanticCase(
        "http://192.0.2.13/login/verify", PHISHING,
        "ip-host", "credential path on a bare IP literal",
    ),
    SemanticCase(
        "http://203.0.113.77/admin/signin", PHISHING,
        "ip-host", "admin sign-in on an IP literal",
    ),
    # Punycode homograph.
    SemanticCase(
        "https://xn--pypal-4ve.com/secure/login/confirm", PHISHING,
        "punycode", "punycode host with credential path",
    ),
    # Keywords in the query string.
    SemanticCase(
        "https://www.bank.example.com/redirect?verify=account&password=reset", PHISHING,
        "credential-query", "credentials passed as query parameters",
    ),
    SemanticCase(
        "https://update-info.example.net/secure-login-session-confirm.php", PHISHING,
        "deep-path", "five stacked credential segments",
    ),
]


ALL_CASES: list[SemanticCase] = LEGITIMATE_CASES + PHISHING_CASES


def legitimate_urls() -> list[str]:
    return [c.url for c in LEGITIMATE_CASES]


def phishing_urls() -> list[str]:
    return [c.url for c in PHISHING_CASES]


def categories() -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in ALL_CASES:
        counts[case.category] = counts.get(case.category, 0) + 1
    return counts


# Domains known to be legitimate, used to check false-positive behaviour
# on real-world structural patterns. Deliberately small and hand-picked.
REAL_WORLD_LEGITIMATE = [
    "https://github.com/anthropics",
    "https://docs.python.org/3/library/asyncio.html",
    "https://developer.mozilla.org/en-US/docs/Web",
    "https://en.wikipedia.org/wiki/Main_Page",
    "https://stackoverflow.com/questions/1",
    "https://arxiv.org/abs/2301.00001",
    "https://www.youtube.com/watch?v=x",
    "https://openai.com/research",
    "https://www.coursera.org/learn/machine-learning",
    "https://www.university.edu.sa",
    "https://www.nasa.gov",
    "https://news.ycombinator.com",
    "https://www.google.com",
    "https://gitlab.com/group/subgroup/project",
]