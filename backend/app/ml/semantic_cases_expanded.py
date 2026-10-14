"""
EXPANDED semantic holdout — legitimate URLs, category-balanced.

WHY A SEPARATE FILE
------------------
`semantic_cases.py` is the shipped regression suite. Its fourteen
REAL_WORLD_LEGITIMATE URLs are the exact set that diagnosed v1, and
they must stay byte-identical forever: a regression suite that gets
edited to match the model's current behaviour is not a regression
suite. So this file ADDS to the evaluation surface and modifies nothing.

HOLDOUT-ONLY, AND ENFORCED AS SUCH
----------------------------------
Every URL here is a well-known legitimate service. Several of these
hosts — github.com, wikipedia.org, stackoverflow.com, youtube.com —
are among the most frequent domains in every legitimate corpus in hand.
If any of them were allowed into training, a low false-positive rate on
this set would be memorisation dressed up as generalisation, and the
number would be worse than meaningless: it would be actively
misleading, because it would look like evidence of exactly the
robustness Phase 2E is trying to demonstrate.

`assert_not_in_training()` therefore exists and the Phase 2E runner
calls it on every training set before training. It is a hard abort,
not a warning.

CATEGORY BALANCE
----------------
The original 14 skew heavily toward documentation and developer sites.
v1's false positives were concentrated there, so a suite dominated by
documentation would let a model that has merely learned "documentation
URLs are safe" score well. These categories are chosen to span the
shapes that Phase 2C/2D showed the model actually gets wrong: long
query strings, numeric-heavy paths, deep nesting, many subdomains,
punycode-free internationalised hosts, and short apex domains.

Every URL is a real, publicly known host or an RFC-reserved example
domain. Nothing is fetched; these are strings only.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ml.datasets import LEGITIMATE
from app.ml.semantic_cases import SemanticCase

__all__ = [
    "EXPANDED_CATEGORIES",
    "EXPANDED_LEGITIMATE_CASES",
    "EXPANDED_CASES",
    "assert_not_in_training",
]


# ====================================================================
# THE SET — one block per category, with the shape each one defends
# ====================================================================

EXPANDED_LEGITIMATE_CASES: list[SemanticCase] = [
    # --- documentation & reference ---------------------------------
    # Deep, multi-segment, long paths. The shape that broke v1.
    SemanticCase(
        "https://docs.djangoproject.com/en/5.0/ref/models/fields/",
        LEGITIMATE, "documentation",
        "five-segment documentation path under a versioned locale prefix",
    ),
    SemanticCase(
        "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/",
        LEGITIMATE, "documentation",
        "long nested documentation path on a hyphenated project domain",
    ),
    SemanticCase(
        "https://www.postgresql.org/docs/current/using-explain.html",
        LEGITIMATE, "documentation",
        "versioned SQL manual page with a hyphenated filename",
    ),
    SemanticCase(
        "https://learn.microsoft.com/en-us/dotnet/api/system.string.format",
        LEGITIMATE, "documentation",
        "API reference page with dot-separated API path segments",
    ),

    # --- source control & developer platforms ----------------------
    # High digit and underscore counts, deep paths. Digit-heavy paths
    # are a phishing signature; issue numbers are not.
    SemanticCase(
        "https://github.com/python/cpython/pull/118132",
        LEGITIMATE, "source_control",
        "repository path with a numeric pull-request identifier",
    ),
    SemanticCase(
        "https://gitlab.com/gitlab-org/gitlab/-/issues/428659",
        LEGITIMATE, "source_control",
        "issue path using GitLab's dash-prefixed route convention",
    ),
    SemanticCase(
        "https://bitbucket.org/atlassian/python-bitbucket/src/master/README.rst",
        LEGITIMATE, "source_control",
        "deep source path ending in a documentation source file",
    ),

    # --- academic & encyclopaedic ----------------------------------
    SemanticCase(
        "https://en.wikipedia.org/wiki/Phishing",
        LEGITIMATE, "encyclopaedic",
        "high-entropy encyclopaedia article title with underscores",
    ),
    SemanticCase(
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8474333/",
        LEGITIMATE, "academic",
        "numeric article identifier path with a trailing slash",
    ),
    SemanticCase(
        "https://scholar.google.com/scholar?q=phishing+detection+deep+learning",
        LEGITIMATE, "academic",
        "multi-term search query with plus-encoded spaces",
    ),

    # --- news & long query strings ---------------------------------
    # The query-heavy category. A model that never saw a long
    # parameterised legitimate URL treats every query as an attack.
    SemanticCase(
        "https://www.reuters.com/world/middle-east/analysis-2026-10-04/",
        LEGITIMATE, "news",
        "dated news path with several hyphenated segments",
    ),
    SemanticCase(
        "https://www.bbc.co.uk/news/articles/c4g7q2xv1m9o",
        LEGITIMATE, "news",
        "opaque alphanumeric article slug on a two-letter ccTLD",
    ),
    SemanticCase(
        "https://www.theguardian.com/environment/2026/oct/04/climate-report-2026",
        LEGITIMATE, "news",
        "date-stamped section path with numeric year and month",
    ),

    # --- government & public services ------------------------------
    # Multi-level civic domains and long numeric form routes.
    SemanticCase(
        "https://www.gov.uk/browse/abroad/passports/driving-abroad",
        LEGITIMATE, "government",
        "nested civic service path with hyphenated leaf segments",
    ),
    SemanticCase(
        "https://www.irs.gov/forms-pubs/about-form-w-9",
        LEGITIMATE, "government",
        "tax form path with an alphanumeric form identifier",
    ),
    SemanticCase(
        "https://services.health.gov.sa/en/COVID-19",
        LEGITIMATE, "government",
        "public health service subdomain under a national ccTLD",
    ),

    # --- commerce & finance ----------------------------------------
    # Long numeric paths, deep subdomains and session-like query
    # strings — every shape a rule-based engine over-flags.
    SemanticCase(
        "https://www.amazon.com/dp/B08N5WRWNW/ref=sr_1_3",
        LEGITIMATE, "commerce",
        "product ASIN path with a tracking reference query",
    ),
    SemanticCase(
        "https://checkout.stripe.com/pay/cs_test_a1B2c3D4e5F6",
        LEGITIMATE, "commerce",
        "checkout subdomain with a high-entropy session path",
    ),
    SemanticCase(
        "https://www.nytimes.com/2026/10/04/business/energy-market-report.html",
        LEGITIMATE, "news",
        "date-partitioned article path with a file extension",
    ),

    # --- social & media --------------------------------------------
    # The apex-heavy category. A model that learned 'no path means
    # safe' also fails here in the other direction.
    SemanticCase(
        "https://www.linkedin.com/feed/",
        LEGITIMATE, "social",
        "short trailing-slash path on a professional network",
    ),
    SemanticCase(
        "https://x.com/BASIRAH/status/1823456789012345678",
        LEGITIMATE, "social",
        "social post path with a 19-digit status identifier",
    ),
    SemanticCase(
        "https://www.instagram.com/p/CSAb3dEfGh1/",
        LEGITIMATE, "social",
        "short media permalink with mixed-case identifier",
    ),

    # --- cloud, CDN & developer tooling ----------------------------
    # Very deep subdomains and wildcard-style hosts.
    SemanticCase(
        "https://console.aws.amazon.com/ec2/home?region=eu-west-1#Instances:",
        LEGITIMATE, "cloud",
        "cloud console path with a query and a URL fragment",
    ),
    SemanticCase(
        "https://raw.githubusercontent.com/torvalds/linux/master/README",
        LEGITIMATE, "cloud",
        "raw content CDN host with a three-segment path",
    ),
    SemanticCase(
        "https://registry.npmjs.org/@babel/core/latest",
        LEGITIMATE, "cloud",
        "package registry path with a scoped package name and version",
    ),

    # --- education & research --------------------------------------
    SemanticCase(
        "https://www.coursera.org/learn/machine-learning-supervised",
        LEGITIMATE, "education",
        "course path with a long hyphenated slug",
    ),
    SemanticCase(
        "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/",
        LEGITIMATE, "education",
        "course catalogue path with a course number and full term",
    ),
    SemanticCase(
        "https://www.edx.org/course/mitx-6-0001x-introduction-to-computer-science",
        LEGITIMATE, "education",
        "course path containing both a course number and a slug",
    ),

    # --- short apex domains ----------------------------------------
    # The bare-host category. These are legitimate and carry no path at
    # all; they are the counterweight to any 'a path means phishing'
    # shortcut learned from a corpus where legitimate URLs are 0%
    # path-bearing.
    SemanticCase(
        "https://www.wikipedia.org",
        LEGITIMATE, "apex_domain",
        "bare apex domain with no path",
    ),
    SemanticCase(
        "https://stackoverflow.com",
        LEGITIMATE, "apex_domain",
        "bare apex domain for a developer Q&A site",
    ),
    SemanticCase(
        "https://arxiv.org",
        LEGITIMATE, "apex_domain",
        "bare apex domain for a preprint archive",
    ),

    # --- internationalised / non-ASCII ------------------------------
    # Non-ASCII and multi-label hosts, which the lexical features
    # handle least well.
    SemanticCase(
        "https://www.xn--80ak6aa92e.com/",
        LEGITIMATE, "internationalised",
        "punycode-encoded internationalised domain",
    ),
    SemanticCase(
        "https://例え.テスト/",
        LEGITIMATE, "internationalised",
        "non-ASCII internationalised domain label",
    ),

    # --- parameterised & tracking URLs ------------------------------
    # Deliberately query-heavy legitimate URLs, including one that
    # resembles a redirect. The distinction from a phishing URL is the
    # registrable domain, which is exactly what a lexical model must
    # learn to rely on.
    SemanticCase(
        "https://www.google.com/search?q=how+to+report+phishing&num=20",
        LEGITIMATE, "parameterised",
        "search URL with multiple query parameters",
    ),
    SemanticCase(
        "https://example.com/page?utm_source=newsletter&utm_medium=email&id=12345",
        LEGITIMATE, "parameterised",
        "RFC-reserved example host carrying three tracking parameters",
    ),
    SemanticCase(
        "https://www.linkedin.com/redirect?url=https%3A%2F%2Fexample.org%2Farticle",
        LEGITIMATE, "parameterised",
        "legitimate redirect endpoint on a trusted registrable domain",
    ),
]


# Categories, declared so a caller can verify balance rather than
# assuming it.
EXPANDED_CATEGORIES: list[str] = sorted(
    {case.category for case in EXPANDED_LEGITIMATE_CASES}
)

EXPANDED_CASES: list[SemanticCase] = list(EXPANDED_LEGITIMATE_CASES)


def assert_not_in_training(training_urls: object, training_domains: object) -> None:
    """Abort if any holdout URL or its domain appears in training.

    Takes the training URL set and the training registered-domain set.
    Domain-level checking is the stronger assertion and is the one that
    matters: a model that has seen `en.wikipedia.org/wiki/Phishing` has
    memorised the exact string, and a model that has seen any URL on
    `en.wikipedia.org` has memorised the host's URL shapes.

    URL membership alone is too weak to catch either case, which is why
    both are checked.
    """
    url_set = {str(u).strip().lower() for u in training_urls}  # type: ignore[union-attr]
    domain_set = {str(d).strip().lower() for d in training_domains}  # type: ignore[union-attr]

    from app.services.url_analyzer import InvalidURLError, normalize

    leaked_urls: list[str] = []
    leaked_domains: list[str] = []
    for case in EXPANDED_LEGITIMATE_CASES:
        key = case.url.strip().lower()
        if key in url_set:
            leaked_urls.append(case.url)
        try:
            parsed = normalize(case.url)
        except InvalidURLError:
            continue
        domain = (parsed.registered_domain or parsed.hostname).lower()
        if domain in domain_set:
            leaked_domains.append(f"{case.url} -> {domain}")

    if leaked_urls or leaked_domains:
        parts = []
        if leaked_urls:
            parts.append(
                f"{len(leaked_urls)} expanded-holdout URL(s) present in "
                f"training verbatim: {leaked_urls[:5]}"
            )
        if leaked_domains:
            parts.append(
                f"{len(leaked_domains)} expanded-holdout registered domain(s) "
                f"present in training: {leaked_domains[:5]}"
            )
        raise AssertionError(
            "EXPANDED SEMANTIC HOLDOUT LEAKED INTO TRAINING — "
            + "; ".join(parts)
            + ". The expanded set is holdout-only; its scores are "
            "memorisation if it appears in training."
        )