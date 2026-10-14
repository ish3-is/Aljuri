"""
Corpus quality gate.

Phase 2B trained a model on PhiUSIIL that reported ROC-AUC 0.998 while
being exactly inverted, then produced a second model that flagged
`github.com/anthropics` as phishing. Both defects were invisible to every
accuracy metric, because the metrics were computed against the same
defective data.

This module is the answer: twelve structural checks that must pass before
any training run is allowed to proceed. It is a GATE, not a report — a
failed critical check aborts the run.

The checks are ordered from "will silently corrupt labels" to
"deserves attention", because not all defects are equally dangerous:

    CRITICAL  training must abort
    WARNING   recorded, training may proceed

Every check returns measured values, never a pass/fail guess. A check
that cannot be evaluated is itself a failure: silently skipping a check
is how these defects survived in the first place.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence

from app.ml.datasets import (
    LEGITIMATE,
    PHISHING,
    AuditedRow,
    LabelOrientationError,
    detect_label_orientation,
)

RESULT_DIR = Path(__file__).resolve().parents[2] / "results" / "phase2c"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    """One gate check."""

    check_id: str
    name: str
    verdict: Verdict
    severity: Severity
    measured: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    @property
    def blocking(self) -> bool:
        return self.verdict is Verdict.FAIL and self.severity is Severity.CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "verdict": self.verdict.value,
            "severity": self.severity.value,
            "blocking": self.blocking,
            "measured": self.measured,
            "message": self.message,
        }


@dataclass
class CorpusQualityReport:
    """The full gate result for one corpus."""

    corpus: str
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.verdict is Verdict.FAIL]

    @property
    def blocking_failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.blocking]

    @property
    def passed(self) -> bool:
        return not self.blocking_failures

    def get(self, check_id: str) -> CheckResult | None:
        for check in self.checks:
            if check.check_id == check_id:
                return check
        return None

    def measured(self, check_id: str) -> dict[str, Any]:
        check = self.get(check_id)
        return check.measured if check else {}

    def summary(self) -> dict[str, Any]:
        return {
            "corpus": self.corpus,
            "passed": self.passed,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.verdict is Verdict.PASS),
            "failed_checks": len(self.failures),
            "blocking_failures": [c.check_id for c in self.blocking_failures],
            "checks": [c.to_dict() for c in self.checks],
        }

    def write(self, directory: Path | None = None) -> Path:
        target = (directory or RESULT_DIR) / "corpus_audit"
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"{self.corpus}_gate.json"
        path.write_text(json.dumps(self.summary(), indent=2, default=str), encoding="utf-8")
        return path

    def enforce(self) -> "CorpusQualityReport":
        """Abort if any critical check failed.

        Available on the report so callers can do
        `gate_corpus(...).enforce()` without holding the gate object.
        """
        if self.passed:
            return self
        lines = [
            f"  - {c.check_id} ({c.severity.value}): {c.message}"
            for c in self.blocking_failures
        ]
        raise CorpusQualityError(
            f"Corpus '{self.corpus}' failed {len(self.blocking_failures)} "
            f"critical quality check(s):\n" + "\n".join(lines)
        )


class CorpusQualityError(RuntimeError):
    """Raised when a corpus fails a critical gate check.

    Training must abort. This is not advisory.
    """


# ====================================================================
# THE GATE
# ====================================================================


class CorpusQualityGate:
    """Runs the twelve structural checks against one corpus."""

    # Thresholds. Chosen from the corpora in hand and stated explicitly
    # so a future corpus can be judged against a documented rule rather
    # than a vibe.
    MAX_MALFORMED_RATE = 0.02
    MAX_DUPLICATE_RATE = 0.05
    MAX_CONFLICT_RATE = 0.0001
    PATH_PRESENCE_IMBALANCE = 0.15
    """Minimum gap between the two classes' path-presence rates that
    counts as a class proxy.

    Set to 0.15, not 0.98. PhiUSIIL measures legitimate 0.000 vs
    phishing 0.597 — a gap of 0.60, far from perfect separation, yet
    still severe enough that 'carries a path' becomes a dominant
    training signal. An earlier threshold of 0.98 passed this corpus,
    which is exactly the failure mode this module exists to prevent.
    A gap above this threshold is a proxy regardless of direction.
    """

    # --- Phase 2D: legitimate-corpus realism checks (C13-C18) ---------
    #
    # C06 asks "does this corpus contain a class proxy?". C13-C18 ask the
    # complementary question about a LEGITIMATE corpus: "does this corpus
    # look like the legitimate traffic the product will actually see?"
    #
    # They are BLOCKING, because the Phase 2B/2C failure was not a
    # phishing defect at all — it was a legitimate-class defect. A
    # legitimate corpus that is almost entirely bare domains teaches the
    # model that a path is evidence of an attack, and that model then
    # flags docs.python.org and github.com/anthropics. Those two URLs
    # differ from a phishing URL in every respect that matters, and were
    # still classified at p > 0.99999 by v1.
    #
    # So a "benign" corpus must be MEASURED against real legitimate
    # traffic, not accepted on its label. Thresholds below are floors:
    # a corpus below the floor cannot represent the deployed
    # distribution and must not be trained on.

    MIN_LEGITIMATE_PATH_RATE = 0.25
    """Minimum share of legitimate URLs carrying a non-trivial path.

    0.25 is deliberately low. Measured real legitimate traffic is far
    above it — the Phase 2D candidate corpus measures 87.58% — but a
    corpus at 0% (PhiUSIIL) or at 2% is not a legitimate corpus, it is
    a domain list.
    """

    MIN_LEGITIMATE_QUERY_RATE = 0.05
    """Minimum share of legitimate URLs carrying a query string.

    Real traffic is ~12% (measured). Query presence is a distinct
    structural signal from path presence: a model that never saw a
    legitimate query string will treat any parameterised URL as
    suspicious.
    """

    MIN_LEGITIMATE_DEEP_PATH_RATE = 0.05
    """Minimum share of legitimate URLs with a path of depth >= 2.

    Depth 2 covers '/blog/post', '/docs/api/v2', '/en-US/docs/Web'.
    Shallow one-segment paths are the easy case; nested paths are what
    real documentation and application sites are made of, and they are
    where the model's length and entropy features misfire hardest.
    """

    MIN_LEGITIMATE_DOMAINS_PER_ROW = 0.10
    """Minimum distinct registered domains per legitimate row.

    Below 0.10 the legitimate class is a handful of domains repeated
    thousands of times. The model then memorises those domains instead
    of learning legitimate structure, and grouped-domain validation
    reports the collapse.
    """

    MAX_SINGLE_DOMAIN_SHARE = 0.05
    """Maximum share of legitimate rows from one registered domain."""

    MAX_SINGLE_SOURCE_SHARE = 0.90
    """Maximum share of legitimate rows from one source corpus.

    Concentration is a WARNING, not a block: a single-source legitimate
    corpus can be legitimate, but it inherits that source's collection
    methodology, and the audit must say so rather than let it pass
    silently.
    """

    MIN_PATH_RATE_MARGIN_OVER_PHISHING = -0.20
    """How far legitimate path rate may sit BELOW the phishing rate.

    C06 catches path presence as a class proxy when the two classes
    are far apart. This catches the specific asymmetry that produced
    the shipped defect in the opposite direction: a legitimate class
    that is dramatically less path-bearing than the phishing class is
    still teaching 'path => phishing', even if the absolute rate is
    above the C13 floor.
    """

    MAX_SHORTCUT_UNIGRAM_RISK = 0.25
    """Maximum share of legitimate rows whose host is a bare apex domain.

    Measured as a risk indicator rather than a hard defect, because
    genuine apex-domain URLs are legitimate. What matters is that the
    corpus must not be MOSTLY apex domains, and it must carry enough
    path-bearing rows that 'has a path' stops being decisive.
    """

    # --- Phase 2E: HTTPS realism and domain concentration (C19-C22) ---
    #
    # C13-C18 established that a legitimate corpus must LOOK like real
    # legitimate traffic. Phase 2E adds the two properties that the
    # Mendeley source was adopted for and one that guards the sampling
    # stage itself.
    #
    # C19/C20 are concentration checks. They exist because the source
    # adopted in Phase 2E measures top-10 domains at 17.68% of all
    # rows (wikipedia 12,895, youtube 8,627, facebook 8,275), which is
    # high enough that an uncapped corpus would train the model to
    # recognise three popular websites rather than legitimate URL
    # STRUCTURE.
    #
    # C21 is the scheme-realism check, and it is the direct counterpart
    # of C07. C07 asks "does scheme determine the class?"; C21 asks
    # "does the legitimate class carry a realistic scheme MIX?". A
    # legitimate class that is 100% HTTPS teaches the model that http
    # means phishing even though real phishing is mostly HTTPS now —
    # the same inversion that got the scheme features excluded in
    # Phase 2B, arrived at from the other direction.
    #
    # C22 is an ENFORCEMENT check rather than a property check: it
    # verifies that the per-domain cap the sampling strategy claims to
    # apply was actually applied to the rows handed to the gate. A cap
    # that is documented but not enforced is worse than no cap, because
    # the audit records the intent and the training set contradicts it.

    MAX_TOP_DOMAIN_CONCENTRATION = 0.10
    """Maximum share of legitimate rows from the single largest domain.

    WARNING. A legitimate corpus concentrated on one domain is not
    necessarily wrong — a vendor's own site list is legitimate — but it
    inherits that domain's URL shape, and the audit must say so.

    The Phase 2E source measures 3.73%, comfortably inside this. The
    5% ceiling from C15 is retained there as a COMPONENT of the C15
    verdict; this is the standalone, configurable record.
    """

    MAX_TOP10_DOMAIN_CONCENTRATION = 0.40
    """Maximum share of legitimate rows from the ten largest domains.

    WARNING. Deliberately looser than the single-domain ceiling: ten
    domains at 40% is still a corpus with 60% of its rows spanning
    hundreds of thousands of other domains, which is structurally very
    different from a corpus that is one domain repeated.
    """

    MIN_LEGITIMATE_HTTPS_RATE = 0.20
    """Minimum HTTPS share of the legitimate class.

    Real legitimate traffic is overwhelmingly HTTPS, so a low floor is
    the right shape here: the check exists to catch a corpus that is
    entirely one scheme, not to enforce a modern-web statistic on a
    dataset collected a decade ago.
    """

    MAX_LEGITIMATE_HTTPS_RATE = 0.995
    """Maximum HTTPS share of the legitimate class.

    This is the interesting one. At 99.99% — the measured value for the
    Phase 2E source — every legitimate example is HTTPS, so the model
    can reach high in-domain accuracy on 'http => phishing' while
    learning nothing about phishing. That is precisely the shortcut that
    made the scheme features a corpus fingerprint in Phase 2B.

    0.995 rather than 1.0: a corpus that is 100% HTTPS carries no
    contrast at all, so anything at or below 0.995 FAILS, including a
    corpus that is exactly 1.0. The threshold is configurable because a
    caller who can demonstrate a matching http:// legitimate population
    elsewhere is entitled to argue for a different number.
    """

    DOMAIN_CAP_REQUIRED = False
    """Whether C22 is BLOCKING when no cap is declared in context."""

    def __init__(self, corpus: str) -> None:
        self.corpus = corpus
        self.report = CorpusQualityReport(corpus)

    # ----------------------------------------------------------------
    def run(self, rows: Sequence[AuditedRow], **context: Any) -> CorpusQualityReport:
        """Execute every check. Order matters only for readability."""
        if not rows:
            self.report.add(
                CheckResult(
                    "C01_nonempty", "Corpus is non-empty", Verdict.FAIL,
                    Severity.CRITICAL, {}, "no rows supplied",
                )
            )
            return self.report

        self.report.add(self._c01_labels(rows, context))
        self.report.add(self._c02_orientation(context))
        self.report.add(self._c03_missing(rows))
        self.report.add(self._c04_duplicates(rows))
        self.report.add(self._c05_conflicts(rows))
        self.report.add(self._c06_path_presence(rows))
        self.report.add(self._c07_scheme(rows))
        self.report.add(self._c08_domain_repetition(rows))
        self.report.add(self._c10_class_balance(rows))
        self.report.add(self._c11_malformed(rows, context))
        # Phase 2D legitimate-corpus realism checks. These are gated on
        # the corpus declaring itself a LEGITIMATE corpus via context,
        # because a phishing-only corpus (PhishTank) has no legitimate
        # class to be realistic about and the checks would be vacuous.
        if context.get("legitimate_corpus", True):
            self.report.add(self._c13_path_representation(rows))
            self.report.add(self._c14_query_representation(rows))
            self.report.add(self._c15_domain_diversity(rows))
            self.report.add(self._c16_deep_path_representation(rows))
            self.report.add(self._c17_source_concentration(rows))
            self.report.add(self._c18_shortcut_risk(rows))
            # Phase 2E: HTTPS realism and domain concentration. Gated on
            # the same legitimate_corpus flag for the same reason as
            # C13-C18 — these all describe the legitimate class.
            self.report.add(self._c19_top_domain_concentration(rows))
            self.report.add(self._c20_top10_domain_concentration(rows))
            self.report.add(self._c21_https_realism(rows))
        # C22 is NOT gated on legitimate_corpus: it verifies a sampling
        # claim about the WHOLE row set, so it applies to every corpus,
        # including phishing-only ones.
        self.report.add(self._c22_domain_cap_enforcement(rows, context))
        return self.report

    def enforce(self) -> CorpusQualityReport:
        """Abort on any critical failure.

        Call this BEFORE featurizing. The whole point is to stop a
        defective corpus from reaching a model.
        """
        if not self.report.passed:
            lines = [
                f"  - {c.check_id} ({c.severity.value}): {c.message}"
                for c in self.report.blocking_failures
            ]
            raise CorpusQualityError(
                f"Corpus '{self.corpus}' failed {len(self.report.blocking_failures)} "
                f"critical quality check(s):\n" + "\n".join(lines)
            )
        return self.report

    # ----------------------------------------------------------------
    # CHECKS
    # ----------------------------------------------------------------

    def _c01_labels(self, rows: Sequence[AuditedRow], context: dict[str, Any]) -> CheckResult:
        """Labels are binary and use the canonical encoding."""
        observed = sorted({r.label for r in rows})
        canonical = {LEGITIMATE, PHISHING}
        ok = set(observed) <= canonical
        return CheckResult(
            "C01_label_encoding",
            "Labels are binary and canonical (0=legitimate, 1=phishing)",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL,
            {
                "distinct_labels": observed,
                "expected": sorted(canonical),
                "declared_orientation": context.get("label_orientation"),
            },
            "" if ok else f"unexpected label values {observed}",
        )

    def _c02_orientation(self, context: dict[str, Any]) -> CheckResult:
        """Numeric orientation was stated, never inferred silently."""
        orientation = context.get("label_orientation")
        textual = context.get("textual_labels", False)
        if orientation in (1, -1):
            return CheckResult(
                "C02_label_orientation", "Label orientation explicitly declared",
                Verdict.PASS, Severity.CRITICAL,
                {"orientation": orientation, "meaning": "1=phishing" if orientation == 1 else "1=legitimate"},
                "",
            )
        if textual:
            return CheckResult(
                "C02_label_orientation", "Label orientation explicitly declared",
                Verdict.PASS, Severity.CRITICAL,
                {"orientation": "textual", "meaning": "resolved from class names"},
                "",
            )
        return CheckResult(
            "C02_label_orientation", "Label orientation explicitly declared",
            Verdict.FAIL, Severity.CRITICAL, {"orientation": orientation},
            "label_orientation was not declared. PhiUSIIL inverts the usual "
            "convention, so an unstated numeric orientation is unsafe.",
        )

    def _c03_missing(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """No row lacks a URL."""
        missing = sum(1 for r in rows if not (r.url or "").strip())
        rate = missing / max(len(rows), 1)
        return CheckResult(
            "C03_missing_urls", "No missing URLs",
            Verdict.PASS if missing == 0 else Verdict.FAIL,
            Severity.CRITICAL, {"missing": missing, "rate": rate},
            "" if missing == 0 else f"{missing} rows have no URL",
        )

    def _c04_duplicates(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Duplicates removed; rate below threshold."""
        seen, duplicates = set(), 0
        for row in rows:
            key = row.normalized.lower()
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
        rate = duplicates / max(len(rows), 1)
        ok = rate <= self.MAX_DUPLICATE_RATE
        return CheckResult(
            "C04_duplicate_urls", "Duplicate URLs removed",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL, {"duplicates": duplicates, "rate": rate,
                                "threshold": self.MAX_DUPLICATE_RATE},
            "" if ok else f"duplicate rate {rate:.4f} exceeds {self.MAX_DUPLICATE_RATE}",
        )

    def _c05_conflicts(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """No URL carries both labels."""
        labels_by_url: dict[str, set[int]] = {}
        for row in rows:
            labels_by_url.setdefault(row.normalized.lower(), set()).add(row.label)
        conflicts = sum(1 for v in labels_by_url.values() if len(v) > 1)
        rate = conflicts / max(len(rows), 1)
        ok = rate <= self.MAX_CONFLICT_RATE
        return CheckResult(
            "C05_conflicting_labels", "No URL carries conflicting labels",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL, {"conflicts": conflicts, "rate": rate,
                                "threshold": self.MAX_CONFLICT_RATE},
            "" if ok else f"{conflicts} URLs carry conflicting labels",
        )

    def _c06_path_presence(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """A class must not be uniquely characterised by path presence.

        This is the check that would have caught the Phase 2B defect:
        0 of 134,850 legitimate URLs had a path, making 'has a path' a
        perfect proxy for phishing.
        """
        stats: dict[int, tuple[int, int]] = {}
        for label in (LEGITIMATE, PHISHING):
            subset = [r for r in rows if r.label == label]
            with_path = sum(
                1
                for r in subset
                if len(r.normalized.split("://")[-1].split("/", 1)) > 1
            )
            stats[label] = (with_path, len(subset))

        rates = {
            "legitimate": stats[LEGITIMATE][0] / max(stats[LEGITIMATE][1], 1),
            "phishing": stats[PHISHING][0] / max(stats[PHISHING][1], 1),
        }
        gap = abs(rates["phishing"] - rates["legitimate"])
        degenerate = gap >= self.PATH_PRESENCE_IMBALANCE

        return CheckResult(
            "C06_path_presence", "Path presence is not a class proxy",
            Verdict.FAIL if degenerate else Verdict.PASS,
            # CRITICAL: this defect produced 9/13 false positives on real
            # legitimate URLs, which is worse than having no model.
            Severity.CRITICAL,
            {
                "path_presence_rate_legitimate": rates["legitimate"],
                "path_presence_rate_phishing": rates["phishing"],
                "gap": gap,
                "counts": {str(k): {"with_path": v[0], "total": v[1]} for k, v in stats.items()},
            },
            (
                f"path presence strongly separates the classes "
                f"(legitimate {rates['legitimate']:.3f} vs phishing "
                f"{rates['phishing']:.3f}, gap {gap:.3f}); 'has a path' is a "
                f"corpus artifact, not a phishing signal"
            )
            if degenerate
            else "",
        )

    def _c07_scheme(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Scheme distribution is recorded and not class-determining."""
        by_class: dict[int, Counter] = {LEGITIMATE: Counter(), PHISHING: Counter()}
        for row in rows:
            by_class[row.label][row.scheme] += 1
        rates = {
            "legitimate": by_class[LEGITIMATE]["https"] / max(sum(by_class[LEGITIMATE].values()), 1),
            "phishing": by_class[PHISHING]["https"] / max(sum(by_class[PHISHING].values()), 1),
        }
        gap = abs(rates["phishing"] - rates["legitimate"])
        degenerate = gap >= 0.98
        return CheckResult(
            "C07_scheme_distribution", "HTTPS is not a class proxy",
            Verdict.FAIL if degenerate else Verdict.PASS,
            Severity.WARNING,
            {
                "https_rate_legitimate": rates["legitimate"],
                "https_rate_phishing": rates["phishing"],
                "gap": gap,
                "schemes_legitimate": dict(by_class[LEGITIMATE]),
                "schemes_phishing": dict(by_class[PHISHING]),
            },
            (
                f"scheme nearly determines the class (gap {gap:.3f}); exclude "
                f"scheme features from model input"
            )
            if degenerate
            else "",
        )

    def _c08_domain_repetition(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Domain repetition is measured, because it dictates splitting."""
        counts: Counter = Counter(r.registered_domain for r in rows)
        repeated = sum(1 for v in counts.values() if v > 1)
        return CheckResult(
            "C08_domain_repetition", "Registered-domain repetition measured",
            Verdict.PASS, Severity.WARNING,
            {
                "distinct_domains": len(counts),
                "domains_repeated": repeated,
                "rows_in_repeated_domains": sum(v for v in counts.values() if v > 1),
                "max_urls_per_domain": max(counts.values()) if counts else 0,
            },
            "grouped-domain splitting is mandatory" if repeated else "",
        )

    def _c10_class_balance(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Both classes present and neither vanishingly small."""
        counts = Counter(r.label for r in rows)
        legit, phish = counts.get(LEGITIMATE, 0), counts.get(PHISHING, 0)
        total = max(legit + phish, 1)
        minority_rate = min(legit, phish) / total
        ok = legit > 0 and phish > 0 and minority_rate >= 0.01
        return CheckResult(
            "C10_class_balance", "Both classes adequately represented",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.WARNING,
            {"legitimate": legit, "phishing": phish,
             "phishing_rate": phish / total, "minority_rate": minority_rate},
            "" if ok else "one class is absent or vanishingly rare",
        )

    def _c11_malformed(self, rows: Sequence[AuditedRow], context: dict[str, Any]) -> CheckResult:
        """Malformed rate is measured and below threshold."""
        malformed = int(context.get("malformed", 0))
        raw_total = int(context.get("raw_rows", len(rows)))
        rate = malformed / max(raw_total, 1)
        ok = rate <= self.MAX_MALFORMED_RATE
        return CheckResult(
            "C11_malformed_rate", "Malformed URL rate below threshold",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL,
            {"malformed": malformed, "raw_rows": raw_total, "rate": rate,
             "threshold": self.MAX_MALFORMED_RATE},
            "" if ok else f"malformed rate {rate:.4f} exceeds {self.MAX_MALFORMED_RATE}",
        )

    # ----------------------------------------------------------------
    # PHASE 2D — LEGITIMATE-CORPUS REALISM (C13-C18)
    #
    # C06 asks whether a corpus contains a CLASS PROXY. These six ask
    # the opposite and equally necessary question: whether the
    # legitimate class resembles legitimate traffic at all.
    #
    # Every one of them is BLOCKING. The reason is not procedural. The
    # shipped v1 model flagged 10 of 14 well-known legitimate URLs, and
    # every one of those failures traces to the legitimate class being
    # structurally unlike real legitimate traffic — PhiUSIIL's
    # legitimate rows are 0% path-bearing. A corpus metric cannot see
    # that defect because the defect is in the class the metric is
    # scoring against itself.
    # ----------------------------------------------------------------

    # Structural decomposition of a normalised URL. Written as a helper
    # rather than repeated inline six times so that C13, C14, C16 and
    # C18 cannot disagree about what "has a path" means. C06's inline
    # version is left untouched: changing a Phase 2C check's semantics
    # would silently alter previously recorded audit output.
    @staticmethod
    def _structure(normalized: str) -> tuple[list[str], str]:
        """(non-empty path segments, query) for a normalised URL."""
        after_scheme = normalized.split("://", 1)[-1]
        authority, _, remainder = after_scheme.partition("/")
        path_part = remainder if remainder else ""
        query = ""
        if "?" in path_part:
            path_part, _, query = path_part.partition("?")
        query = query.split("#", 1)[0]
        segments = [s for s in path_part.split("/") if s]
        return segments, query

    @staticmethod
    def _rate(count: int, total: int) -> float:
        return count / total if total else 0.0

    def _legitimate_stats(self, rows: Sequence[AuditedRow]) -> dict[str, Any]:
        """One pass over the legitimate class, for every C13-C18 check."""
        subset = [r for r in rows if r.label == LEGITIMATE]
        total = len(subset)

        with_path = 0
        with_query = 0
        deep = 0
        apex_only = 0
        depths: list[int] = []
        domains: Counter = Counter()
        sources: Counter = Counter()

        for row in subset:
            segments, query = self._structure(row.normalized)
            if segments:
                with_path += 1
                depths.append(len(segments))
                if len(segments) >= 2:
                    deep += 1
            if query:
                with_query += 1
            # A bare apex host with no path and no query is the shape the
            # model must NOT learn as the definition of legitimate.
            if not segments and not query:
                apex_only += 1
            domains[row.registered_domain] += 1
            sources[row.source] += 1

        phish_total = sum(1 for r in rows if r.label == PHISHING)
        phish_with_path = sum(
            1
            for r in rows
            if r.label == PHISHING and self._structure(r.normalized)[0]
        )

        return {
            "legitimate_total": total,
            "phishing_total": phish_total,
            "legitimate_path_rate": self._rate(with_path, total),
            "legitimate_query_rate": self._rate(with_query, total),
            "legitimate_deep_path_rate": self._rate(deep, total),
            "legitimate_apex_only_rate": self._rate(apex_only, total),
            "phishing_path_rate": self._rate(phish_with_path, phish_total),
            "median_path_depth": sorted(depths)[len(depths) // 2] if depths else 0,
            "mean_path_depth": round(sum(depths) / len(depths), 4) if depths else 0.0,
            "max_path_depth": max(depths) if depths else 0,
            "distinct_domains": len(domains),
            "domains_per_row": round(self._rate(len(domains), total), 6),
            "top_domains": domains.most_common(10),
            "max_domain_share": round(
                self._rate(max(domains.values()) if domains else 0, total), 6
            ),
            "sources": dict(sources),
            "max_source_share": round(
                self._rate(max(sources.values()) if sources else 0, total), 6
            ),
        }

    def _c13_path_representation(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Legitimate URLs must carry paths, as real ones do.

        This is the direct inverse of the PhiUSIIL defect. At 0% the
        legitimate class cannot teach the model anything about what a
        legitimate path looks like, so the only path-bearing examples
        the model sees are attacks.
        """
        stats = self._legitimate_stats(rows)
        rate = stats["legitimate_path_rate"]
        floor = self.MIN_LEGITIMATE_PATH_RATE

        ok = stats["legitimate_total"] > 0 and rate >= floor
        return CheckResult(
            "C13_legitimate_path_representation",
            "Legitimate class carries realistic path structure",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL,
            {
                "path_presence_rate_legitimate": rate,
                "minimum_required": floor,
                "measured_reference_real_traffic": 0.8758,
                "median_path_depth": stats["median_path_depth"],
                "mean_path_depth": stats["mean_path_depth"],
                "max_path_depth": stats["max_path_depth"],
                "legitimate_rows": stats["legitimate_total"],
            },
            (
                f"only {rate:.2%} of legitimate URLs carry a path "
                f"(floor {floor:.0%}); this corpus is a domain list, not "
                f"legitimate traffic. A model trained on it learns that a "
                f"path is evidence of phishing."
            )
            if not ok
            else "",
        )

    def _c14_query_representation(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Legitimate URLs must carry query strings.

        Parameters are ubiquitous in real legitimate traffic and absent
        from PhiUSIIL's legitimate class entirely. Without them, every
        parameterised URL is novel to the model at the query features.
        """
        stats = self._legitimate_stats(rows)
        rate = stats["legitimate_query_rate"]
        floor = self.MIN_LEGITIMATE_QUERY_RATE
        ok = stats["legitimate_total"] > 0 and rate >= floor
        return CheckResult(
            "C14_legitimate_query_representation",
            "Legitimate class carries realistic query-string structure",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL,
            {
                "query_presence_rate_legitimate": rate,
                "minimum_required": floor,
                "measured_reference_real_traffic": 0.1178,
                "legitimate_rows": stats["legitimate_total"],
            },
            (
                f"only {rate:.2%} of legitimate URLs carry a query string "
                f"(floor {floor:.0%}); every parameterised legitimate URL is "
                f"unseen structure to a model trained on this corpus"
            )
            if not ok
            else "",
        )

    def _c15_domain_diversity(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """The legitimate class must span many domains.

        Diversity is what makes grouped-domain validation meaningful. A
        legitimate class drawn from a few hundred repeated domains
        teaches those domains, and the model generalises to nothing.
        """
        stats = self._legitimate_stats(rows)
        per_row = stats["domains_per_row"]
        floor = self.MIN_LEGITIMATE_DOMAINS_PER_ROW
        share = stats["max_domain_share"]
        share_ceiling = self.MAX_SINGLE_DOMAIN_SHARE

        ok = per_row >= floor and share <= share_ceiling
        return CheckResult(
            "C15_legitimate_domain_diversity",
            "Legitimate class spans many distinct domains",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL,
            {
                "distinct_domains": stats["distinct_domains"],
                "legitimate_rows": stats["legitimate_total"],
                "domains_per_row": per_row,
                "minimum_domains_per_row": floor,
                "max_single_domain_share": share,
                "max_single_domain_share_ceiling": share_ceiling,
                "top_domains": stats["top_domains"],
            },
            (
                f"legitimate class has {stats['distinct_domains']:,} distinct "
                f"domains across {stats['legitimate_total']:,} rows "
                f"({per_row:.3f}/row, floor {floor}); largest single domain "
                f"contributes {share:.2%}"
            )
            if not ok
            else "",
        )

    def _c16_deep_path_representation(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Nested paths must be present, not just single-segment ones.

        '/about' is easy and appears everywhere. '/en-US/docs/Web/HTTP'
        is what broke v1: long, high-entropy, deep, and completely
        legitimate. A corpus with only depth-1 paths cannot teach the
        model that length and entropy are not automatically suspicious.
        """
        stats = self._legitimate_stats(rows)
        rate = stats["legitimate_deep_path_rate"]
        floor = self.MIN_LEGITIMATE_DEEP_PATH_RATE
        ok = stats["legitimate_total"] > 0 and rate >= floor
        return CheckResult(
            "C16_legitimate_deep_path_representation",
            "Legitimate class contains nested (depth >= 2) paths",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL,
            {
                "deep_path_rate_legitimate": rate,
                "minimum_required": floor,
                "median_path_depth": stats["median_path_depth"],
                "mean_path_depth": stats["mean_path_depth"],
                "max_path_depth": stats["max_path_depth"],
            },
            (
                f"only {rate:.2%} of legitimate URLs have a path of depth "
                f">= 2 (floor {floor:.0%}); the model will see long, nested, "
                f"high-entropy paths exclusively in phishing examples"
            )
            if not ok
            else "",
        )

    def _c17_source_concentration(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """No single source may dominate the legitimate class.

        WARNING rather than CRITICAL: single-sourced legitimate corpora
        are common and can be valid, but the source's collection
        methodology is inherited silently unless it is recorded here.
        """
        stats = self._legitimate_stats(rows)
        share = stats["max_source_share"]
        ceiling = self.MAX_SINGLE_SOURCE_SHARE
        ok = share <= ceiling
        return CheckResult(
            "C17_source_concentration",
            "Legitimate class is not dominated by one source corpus",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.WARNING,
            {
                "max_source_share": share,
                "ceiling": ceiling,
                "sources": stats["sources"],
            },
            (
                f"{share:.2%} of legitimate rows come from a single source; "
                f"the corpus inherits that source's collection methodology"
            )
            if not ok
            else "",
        )

    def _c18_shortcut_risk(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """Combined risk that 'bare host' is the model's shortcut.

        The single-feature checks above each answer one question. This
        one asks the question that actually produced the shipped defect:
        can a trivial rule — "has a path" or "is the host a bare apex
        domain" — recover the label? If a one-bit rule nearly separates
        the classes, the corpus is teaching the shortcut regardless of
        how it scores on C06, C13 and C14 individually.

        A corpus may legitimately be path-heavy; it may not be path-
        DECISIVE. That distinction is the whole point.
        """
        stats = self._legitimate_stats(rows)
        legit_path = stats["legitimate_path_rate"]
        phish_path = stats["phishing_path_rate"]
        legit_apex = stats["legitimate_apex_only_rate"]

        # The two trivial rules, evaluated as single-bit classifiers.
        path_gap = abs(legit_path - phish_path)
        apex_share = legit_apex

        # A bare-host shortcut is dangerous when legitimate traffic is
        # MOSTLY bare hosts AND phishing traffic is mostly not. Either
        # alone is merely a corpus property; together they are the
        # exact shape of the shipped defect.
        shortcut_risk = (
            apex_share >= self.MAX_SHORTCUT_UNIGRAM_RISK and path_gap >= 0.20
        )

        return CheckResult(
            "C18_suspicious_shortcut_risk",
            "No trivial single-bit rule nearly recovers the label",
            Verdict.FAIL if shortcut_risk else Verdict.PASS,
            Severity.CRITICAL,
            {
                "legitimate_apex_only_rate": apex_share,
                "max_apex_only_rate": self.MAX_SHORTCUT_UNIGRAM_RISK,
                "path_rate_gap": round(path_gap, 6),
                "path_presence_rate_legitimate": legit_path,
                "path_presence_rate_phishing": phish_path,
                # Accuracy of the one-bit rule "flag iff the URL has a
                # path". Each class contributes the half of itself the
                # rule gets right: legitimate rows when they are bare,
                # phishing rows when they are pathed.
                "has_path_rule_accuracy": round(
                    (
                        legit_apex * stats["legitimate_total"]
                        + phish_path * stats["phishing_total"]
                    )
                    / max(stats["legitimate_total"] + stats["phishing_total"], 1),
                    6,
                ),
                "has_path_rule_shortcut": bool(shortcut_risk),
                "interpretation": (
                    "a one-bit 'has a path' rule separates the classes, so "
                    "the model can achieve high accuracy while learning "
                    "nothing about phishing"
                    if shortcut_risk
                    else "no trivial rule separates the classes; the model "
                    "must use lexical and structural detail"
                ),
            },
            (
                f"{apex_share:.2%} of legitimate URLs are bare hosts with no "
                f"path and no query, while the path-rate gap between classes "
                f"is {path_gap:.3f}. 'Has a path' nearly determines the "
                f"label, which is how v1 learned to call "
                f"docs.python.org phishing."
            )
            if shortcut_risk
            else "",
        )


# ----------------------------------------------------------------
    # PHASE 2E — HTTPS REALISM AND DOMAIN CONCENTRATION (C19-C22)
    #
    # C19/C20 answer "is this corpus one domain, or ten domains, wearing
    # a corpus's clothes?". C21 answers the scheme question C07 could
    # not: C07 measures whether scheme separates the two classes INSIDE
    # a corpus, while C21 measures whether the legitimate class has
    # enough scheme variety to teach the difference between 'http' and
    # 'that URL is dangerous'.
    #
    # C22 is different in kind from every other check here. It does not
    # measure a property of the data; it verifies that a documented
    # sampling decision was actually carried out on the exact rows
    # being gated.
    # ----------------------------------------------------------------

    def _c19_top_domain_concentration(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """The single largest domain must not dominate the corpus.

        WARNING, not CRITICAL. Concentration is a property, not a
        defect: 10% from one domain is auditable and survivable, 90%
        is not. The ceiling is what turns the second into the first.
        """
        subset = [r for r in rows if r.label == LEGITIMATE]
        total = len(subset)
        counts: Counter = Counter(r.registered_domain for r in subset)
        top_domain, top_count = (counts.most_common(1) or [("", 0)])[0]
        share = self._rate(top_count, total)
        ceiling = self.MAX_TOP_DOMAIN_CONCENTRATION
        ok = total > 0 and share <= ceiling
        return CheckResult(
            "C19_top_domain_concentration",
            "Single largest domain stays within the concentration ceiling",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.WARNING,
            {
                "top_domain": top_domain,
                "top_domain_rows": top_count,
                "legitimate_rows": total,
                "top_domain_share": round(share, 6),
                "ceiling": ceiling,
                "top_10_domains": counts.most_common(10),
            },
            (
                f"the largest legitimate domain ({top_domain}) contributes "
                f"{share:.2%} of legitimate rows (ceiling {ceiling:.0%}); the "
                f"model can partly memorise it instead of learning legitimate "
                f"URL structure"
            )
            if not ok
            else "",
        )

    def _c20_top10_domain_concentration(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """The ten largest domains together must not dominate the corpus.

        WARNING. A distinct check from C19 because the failure mode is
        different: one domain at 9% passes C19 and is useless, while ten
        domains at 9% each is a corpus that has quietly become a list of
        the ten most popular websites on the internet.
        """
        subset = [r for r in rows if r.label == LEGITIMATE]
        total = len(subset)
        counts: Counter = Counter(r.registered_domain for r in subset)
        top10 = counts.most_common(10)
        share = self._rate(sum(c for _, c in top10), total)
        ceiling = self.MAX_TOP10_DOMAIN_CONCENTRATION
        ok = total > 0 and share <= ceiling
        return CheckResult(
            "C20_top10_domain_concentration",
            "Ten largest domains stay within the joint concentration ceiling",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.WARNING,
            {
                "top_10_rows": sum(c for _, c in top10),
                "legitimate_rows": total,
                "top_10_share": round(share, 6),
                "ceiling": ceiling,
                "distinct_domains": len(counts),
                "domains_per_row": round(self._rate(len(counts), total), 6),
                "top_10_domains": top10,
            },
            (
                f"the ten largest legitimate domains contribute {share:.2%} "
                f"of legitimate rows (ceiling {ceiling:.0%}); a per-domain cap "
                f"is the mechanism that lowers this, and C22 verifies the cap "
                f"was applied"
            )
            if not ok
            else "",
        )

    def _c21_https_realism(self, rows: Sequence[AuditedRow]) -> CheckResult:
        """The legitimate class must carry a realistic SCHEME MIX.

        This is the check the Phase 2E source was adopted to satisfy,
        and it is also the check that source most conspicuously fails:
        99.99% HTTPS. The Phase 2B evidence for excluding uses_https
        and uses_http from the model input was that their class
        association INVERTS between corpora (lift +2.06 on PhiUSIIL,
        -0.89 on MUD 2026), because each corpus collected URLs its own
        way. A legitimate class that is 100% one scheme reproduces that
        defect locally: 'plain http' becomes the answer to every
        phishing question, and it will be wrong against a real attack
        that arrived over http and a real site that did not.

        SEVERITY: WARNING, and the reason is a Phase 2E decision worth
        stating. Every one of C13-C18 is CRITICAL because its defect
        reaches inference — a corpus that teaches 'path => phishing'
        produces a model that flags docs.python.org. C21's defect does
        NOT reach inference, because uses_https and uses_http are
        excluded from model input by feature_schema.MODEL_EXCLUDED_
        FEATURES, so no model can act on 'http => phishing' however
        concentrated the corpus is. Making it blocking would abort
        training on the one corpus that fixes Phase 2D's real defect,
        in exchange for no change in what a user ever sees.

        It is therefore a loud WARNING: recorded, quantified, and
        carried into the promotion decision as a constraint on any
        future attempt to re-enable scheme features. Promoting it to
        CRITICAL is a one-line change for a caller who has removed the
        exclusion.
        """
        subset = [r for r in rows if r.label == LEGITIMATE]
        total = len(subset)
        https = sum(1 for r in subset if r.uses_https)
        rate = self._rate(https, total)
        floor = self.MIN_LEGITIMATE_HTTPS_RATE
        ceiling = self.MAX_LEGITIMATE_HTTPS_RATE
        ok = total > 0 and floor <= rate <= ceiling
        return CheckResult(
            "C21_https_realism",
            "Legitimate class carries a realistic HTTPS/HTTP mix",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.WARNING,
            {
                "https_rate_legitimate": round(rate, 6),
                "https_rows_legitimate": https,
                "http_rows_legitimate": total - https,
                "legitimate_rows": total,
                "minimum_required": floor,
                "maximum_allowed": ceiling,
                "measured_reference_real_traffic": 0.95,
                "scheme_features_are_model_excluded": True,
            },
            (
                f"{rate:.2%} of legitimate URLs are HTTPS (allowed band "
                f"{floor:.0%}-{ceiling:.1%}); with no legitimate http:// "
                f"contrast, 'http => phishing' is learnable from this corpus "
                f"alone. uses_https/uses_http remain excluded from model "
                f"input (feature_schema.MODEL_EXCLUDED_FEATURES), so this "
                f"does not reach inference — but it caps how much scheme "
                f"realism the corpus can actually deliver."
            )
            if not ok
            else "",
        )

    def _c22_domain_cap_enforcement(
        self, rows: Sequence[AuditedRow], context: dict[str, Any]
    ) -> CheckResult:
        """A declared per-domain cap must actually bound the rows.

        An ENFORCEMENT check. The sampling strategy claims a per-domain
        cap; C22 re-derives the observed maximum from the exact rows
        being gated and fails if it exceeds the claim. This is the check
        that makes the cap auditable rather than aspirational — a cap
        documented in a JSON file and not applied to the training set
        would leave the audit describing a corpus that does not exist.
        """
        cap = context.get("domain_cap")
        if cap is None:
            return CheckResult(
                "C22_domain_cap_enforcement",
                "Declared per-domain cap is enforced on the supplied rows",
                Verdict.SKIP,
                Severity.CRITICAL if self.DOMAIN_CAP_REQUIRED else Severity.WARNING,
                {
                    "domain_cap": None,
                    "note": (
                        "no per-domain cap was declared in context, so there "
                        "is nothing to enforce"
                    ),
                },
                "",
            )
        cap = int(cap)
        counts: Counter = Counter(r.registered_domain for r in rows)
        observed_max = max(counts.values()) if counts else 0
        worst_domain = (counts.most_common(1) or [("", 0)])[0][0]
        violating = {d: c for d, c in counts.items() if c > cap}
        ok = observed_max <= cap
        return CheckResult(
            "C22_domain_cap_enforcement",
            "Declared per-domain cap is enforced on the supplied rows",
            Verdict.PASS if ok else Verdict.FAIL,
            Severity.CRITICAL,
            {
                "declared_domain_cap": cap,
                "observed_max_rows_per_domain": observed_max,
                "worst_domain": worst_domain,
                "worst_domain_rows": observed_max,
                "domains_over_cap": len(violating),
                "rows_in_over_cap_domains": sum(violating.values()),
                "rows_gated": len(rows),
                "distinct_domains": len(counts),
            },
            (
                f"the sampling strategy declares a cap of {cap} URLs per "
                f"registered domain, but {worst_domain} contributes "
                f"{observed_max}; {len(violating)} domain(s) exceed the cap. "
                f"The documented sampling and the gated rows disagree."
            )
            if not ok
            else "",
        )


def gate_corpus(
    corpus: str,
    rows: Sequence[AuditedRow],
    *,
    require_path_check: bool = True,
    allow_reversed_path_presence: bool = False,
    **context: Any,
) -> CorpusQualityReport:
    """Run the gate and return the report without raising.

    Call `report.enforce()` (or `gate_and_enforce`) to abort on failure.

    `allow_reversed_path_presence` handles the one case where C06's
    two-sided rule produces a false alarm. C06 fails whenever the two
    classes' path-presence rates differ by >= 0.15, in EITHER direction,
    because both directions make path presence a class proxy. That is
    correct for PhiUSIIL, where legitimate 0.000 vs phishing 0.597 means
    "a path is evidence of an attack".

    It is the wrong verdict for a corpus like the Phase 2D candidate,
    which measures legitimate 0.877 vs phishing 0.457. The gap is real,
    but it points the safe way: the legitimate class now carries MORE
    paths than the phishing class, so the model cannot learn "a path
    means phishing" — the specific failure C06 exists to catch. The
    cost of the reversed gap is the opposite one, reduced sensitivity
    to path-bearing attacks, and that is verified empirically against a
    held-out phishing corpus rather than inferred here.

    So this flag demotes C06 to a warning and leaves the measured value
    in the audit, rather than weakening C06's threshold globally or
    deleting the finding. A caller must opt in explicitly, so the
    reversal can never be assumed.
    """
    gate = CorpusQualityGate(corpus)
    gate.run(rows, **context)
    if not require_path_check:
        check = gate.report.get("C06_path_presence")
        if check is not None and check.blocking:
            # Demote to warning rather than delete: the finding is real
            # and should stay visible in the audit output.
            check.severity = Severity.WARNING
    if allow_reversed_path_presence:
        check = gate.report.get("C06_path_presence")
        if check is not None and check.blocking:
            legitimate = check.measured.get("path_presence_rate_legitimate", 0.0)
            phishing = check.measured.get("path_presence_rate_phishing", 0.0)
            if legitimate > phishing:
                check.severity = Severity.WARNING
                check.message = (
                    f"path presence still separates the classes but in the "
                    f"SAFE direction (legitimate {legitimate:.3f} > phishing "
                    f"{phishing:.3f}). Demoted to warning: the model cannot "
                    f"learn 'path => phishing' from this corpus. The "
                    f"compensating risk is reduced phishing recall on "
                    f"path-bearing attacks, which must be measured on a "
                    f"held-out phishing corpus rather than assumed."
                )
                check.measured["reversed_direction"] = True
    return gate.report


def gate_and_enforce(
    corpus: str, rows: Sequence[AuditedRow], **context: Any
) -> CorpusQualityReport:
    """Run the gate and abort on any critical failure."""
    return gate_corpus(corpus, rows, **context).enforce()


__all__ = [
    "CheckResult",
    "CorpusQualityError",
    "CorpusQualityGate",
    "CorpusQualityReport",
    "Severity",
    "Verdict",
    "gate_and_enforce",
    "gate_corpus",
]