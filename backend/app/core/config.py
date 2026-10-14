"""
BASIRAH — central configuration.

Every tunable constant in the backend lives here so that the graduation
report can cite one file, and so that thresholds are never scattered as
magic numbers through the services.

Nothing in this module is secret. Phase 2 has no credentials, no paid
APIs and no external calls.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository paths, resolved from this file so the backend runs from any
# working directory.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = BACKEND_ROOT / "models"
DATASETS_DIR = BACKEND_ROOT / "datasets"


class Settings(BaseSettings):
    """Runtime settings, overridable via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- service identity ---
    app_name: str = "BASIRAH URL Intelligence Engine"
    version: str = "2.0.0"
    phase: str = "Phase 2 — URL Intelligence"

    # --- CORS ---
    # Development origins only. A production GitHub Pages origin must be
    # added explicitly via BASIRAH_CORS_ORIGINS; wildcard is never used.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # --- input validation ---
    # A URL longer than this is rejected outright rather than analysed:
    # it protects memory and reflects that no legitimate navigational
    # URL approaches this length.
    max_url_length: int = 2048
    # Schemes we are willing to reason about. Everything else is refused
    # at the edge (see services/url_analyzer.py) — we never resolve or
    # dereference a non-navigational scheme.
    allowed_schemes: set[str] = {"http", "https"}

    # --- risk thresholds (centralised) ---
    # Bands map onto BASIRAH's RiskLevel: trusted | caution | high_risk.
    # Thresholds apply to the FINAL RISK score (0-100, higher = riskier).
    high_risk_threshold: float = 60.0
    caution_threshold: float = 30.0

    # --- evidence floors ---
    # Floors guarantee that a category of evidence can never be reported
    # in a band that would misrepresent it, independent of how the
    # individual weights happen to sum. Each is set AT a band boundary,
    # so a floor can only ever lift a score into the next band, never
    # jump it.
    #
    # min_high_severity: a rule we rate high-severity on its own (raw IP
    # host, embedded credentials, punycode) always reaches CAUTION.
    min_high_severity_score: float = 30.0

    # min_corroborating_rules / min_corroborating_score: two or more
    # independent indicators always reach CAUTION. Without this, a URL
    # with genuinely corroborating evidence could still be reported as
    # "trusted" purely because its rule weights happened to sum just
    # under the threshold — an accident of arithmetic, not a judgement.
    min_corroborating_rules: int = 2
    min_corroborating_score: float = 30.0

    # --- risk fusion weights ---
    # final_risk = w_model * model_risk + w_heuristic * heuristic_risk
    #
    # The model is weighted below the heuristics on purpose. A classifier
    # trained on lexical patterns can generalise badly to unseen domains,
    # whereas a triggered rule is a directly inspectable fact about THIS
    # url. Neither dominates: the model contributes the statistical
    # signal, the heuristics contribute the explainable evidence.
    model_weight: float = 0.45
    heuristic_weight: float = 0.55

    # Heuristic risk saturates at this raw weight total, at which point
    # heuristic_risk is treated as 100. Without saturation, five strongly
    # triggered rules would produce a meaningless raw score.
    heuristic_saturation: float = 100.0

    # --- model metadata ---
    model_filename: str = "url_risk_model.joblib"


settings = Settings()


# ====================================================================
# HEURISTIC RULE WEIGHTS
# ====================================================================
# Weights are expressed in the same 0-100 "risk points" space as the
# fused score, so a rule's contribution is directly readable in the API
# response and in a defense.
#
# Calibration rationale (documented for Chapter 5):
#   18-25  strongly indicative on its own, rare in benign URLs
#   12-17  meaningful corroborating signal
#    6-11  weak corroborating signal; never sufficient alone
#    3-5   structural oddity, informational
#
# NO SINGLE RULE is allowed to classify a URL as high risk by itself.
# The risk engine enforces this structurally — see risk_engine.py.

HEURISTIC_WEIGHTS: dict[str, int] = {
    # --- structural identity anomalies (strong) ---
    "IP_HOST": 22,
    "AT_SYMBOL": 20,
    "PUNYCODE": 18,
    # --- obfuscation ---
    "EXCESSIVE_ENCODING": 16,
    "ABNORMAL_PORT": 12,
    "DOUBLE_SLASH": 8,
    # --- shape anomalies ---
    "LONG_URL": 10,
    "LONG_HOSTNAME": 12,
    "LONG_PATH": 8,
    "EXCESSIVE_SUBDOMAINS": 14,
    "HIGH_ENTROPY_HOSTNAME": 15,
    "HIGH_ENTROPY_URL": 10,
    "HIGH_DIGIT_RATIO": 12,
    "EXCESSIVE_HYPHENS": 9,
    # --- lexical ---
    "SUSPICIOUS_KEYWORD_COMBINATION": 13,
    "BRAND_LIKE_TOKEN": 7,
    "SUSPICIOUS_TLD": 11,
    "CREDENTIAL_IN_URL": 14,
}


# ====================================================================
# KEYWORD LEXICON
# ====================================================================
# Terms commonly associated with credential harvesting. A single term is
# NOT treated as evidence — the engine requires a COMBINATION (two or
# more distinct terms, or one term plus a structural anomaly) before
# SUSPICIOUS_KEYWORD_COMBINATION fires.

SUSPICIOUS_KEYWORDS: frozenset[str] = {
    # authentication / account
    "login", "signin", "sign-in", "log-in", "verify", "verification",
    "verified", "secure", "security", "account", "update", "confirm",
    "confirmation", "password", "credential", "credentials", "auth",
    "authentication", "authorize", "reset", "recover", "recovery",
    "unlock", "validate", "session", "token",
    # financial
    "bank", "banking", "wallet", "payment", "pay", "invoice", "billing",
    "transfer", "refund", "credit", "debit", "finance",
    # support / lure
    "support", "helpdesk", "service", "secure-login", "webscr",
    # Arabic equivalents, matched against the percent-decoded string so
    # an Arabic lure term is observable without fetching page content.
    "تسجيل", "دخول", "تحقق", "تحديث", "حساب", "دفع", "فاتورة",
    "كلمة", "مرور", "تأكيد", "امان", "أمان",
}

# Terms that legitimately appear in real institutional URLs. Used ONLY
# to soften (never to cancel) keyword scoring — a brand-like token in a
# domain that is not the brand's own domain is itself an observation.
BRAND_TOKENS: frozenset[str] = {
    "paypal", "apple", "microsoft", "google", "amazon", "netflix",
    "facebook", "instagram", "linkedin", "twitter", "bank", "visa",
    "mastercard", "coinbase", "binance", "metamask", "steam", "adobe",
    "dropbox", "office365", "outlook", "gmail", "yahoo", "chase",
    "wellsfargo", "citibank", "alrajhi", "albaraka", "riyadbank",
}

# Top-level domains disproportionately used for abuse. Listed as a
# heuristic observation with a modest weight, never as proof.
SUSPICIOUS_TLDS: frozenset[str] = {
    "zip", "mov", "top", "xyz", "click", "country", "gq", "cf", "tk",
    "ml", "ga", "work", "review", "rest", "quest", "link", "loan",
    "download", "stream", "racing", "party", "date", "faith", "win",
    "bid", "trade", "accountant", "science", "cricket", "kim",
    "men", "buzz", "monster", "lol", "icu",
}


# ====================================================================
# STRUCTURAL THRESHOLDS
# ====================================================================
# Each threshold is the point at which the corresponding rule triggers.
# Values are chosen from the shape of ordinary navigational URLs, not
# tuned to any dataset.

THRESHOLDS: dict[str, float] = {
    # Lengths
    "long_url": 75.0,
    "long_hostname": 40.0,
    "long_path": 45.0,
    "long_registered_domain": 30.0,
    # Structure
    "excessive_subdomains": 3.0,
    "excessive_hyphens": 3.0,
    # Shannon entropy (bits per character, on the lowercase alphanumeric set)
    "high_entropy_hostname": 3.60,
    "high_entropy_url": 4.3,
    # Composition ratios (0-1)
    "high_digit_ratio": 0.30,
    "high_special_ratio": 0.35,
    # Obfuscation
    "excessive_encoding_ratio": 0.15,
    "double_slash_count": 1.0,
    # Keywords
    "suspicious_keyword_count": 2.0,
    # Ports considered unusual for ordinary web navigation.
    "allowed_web_ports": {80, 443, 8080, 8443},
    # Hostname shape
    "brand_token_min_surrounding_length": 12.0,
}
