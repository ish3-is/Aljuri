"""
Corpus adapters.

Each corpus is read through its own adapter, which is responsible for
exactly one thing: declaring, in words, what its label column MEANS.

Phase 2B's most damaging defect was an adapter that assumed PhiUSIIL
followed the usual convention. It did not, and every downstream number
was inverted while the model still reported AUC 0.998.

So the contract here is narrow and deliberate:

  * an adapter must know, from its own documentation, whether 1 means
    phishing or legitimate;
  * it must SAY so, and the audit must record it;
  * it may not infer numeric orientation from data, because numeric data
    cannot tell you;
  * it must not expose corpus-specific columns to the feature matrix.

The last point is why adapters exist as a separate layer rather than
being folded into the experiment script: MUD ships 100 columns of which
roughly 90 are feature-like, and letting any of them near the matrix
would reintroduce the training-serving skew that Phase 2B spent its
whole length eliminating.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from app.ml.datasets import (
    LEGITIMATE,
    PHISHING,
    AuditedRow,
    LabelOrientationError,
)

csv.field_size_limit(10**9)

BACKEND = Path(__file__).resolve().parents[2]
RAW = BACKEND / "datasets" / "raw"


@dataclass(frozen=True)
class LabelSemantics:
    """What a corpus's label column means, stated explicitly."""

    corpus: str
    zero_means: str
    one_means: str
    orientation: int
    """+1 if 1 = phishing, -1 if 1 = legitimate."""
    documented_source: str

    def normalize(self, raw_value: int) -> int:
        """Map a raw dataset label onto 0=legitimate / 1=phishing."""
        if raw_value == 1:
            return PHISHING if self.orientation == 1 else LEGITIMATE
        return LEGITIMATE if self.orientation == 1 else PHISHING

    def to_dict(self) -> dict[str, object]:
        return {
            "corpus": self.corpus,
            "zero_means": self.zero_means,
            "one_means": self.one_means,
            "orientation": self.orientation,
            "documented_source": self.documented_source,
        }


class CorpusAdapter:
    """Base adapter. Subclasses declare their semantics and yield rows."""

    corpus = "base"
    semantics: LabelSemantics

    def load(self) -> list[AuditedRow]:  # pragma: no cover - abstract
        raise NotImplementedError

    def context(self) -> dict[str, object]:
        """Extra context for the corpus quality gate."""
        return {}


# ====================================================================
# PHIUSIIL
# ====================================================================

# Stated, not inferred. From the UCI dataset page for id 967:
#   "Label 1 corresponds to a legitimate URL, label 0 to a phishing URL."
PHASUSIIL_SEMANTICS = LabelSemantics(
    corpus="phiusil",
    zero_means="phishing",
    one_means="legitimate",
    orientation=-1,
    documented_source=(
        "UCI dataset 967 documentation: 'Label 1 corresponds to a "
        "legitimate URL, label 0 to a phishing URL.'"
    ),
)


class PhiUSIILAdapter(CorpusAdapter):
    """PhiUSIIL Phishing URL Dataset (UCI id 967).

    Only URL and label are read. The 54 precomputed columns are ignored:
    many derive from page content, which does not exist during BASIRAH's
    URL-only inference.
    """

    corpus = "phiusil"
    semantics = PHASUSIIL_SEMANTICS

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (RAW / "phiusil_raw.csv")

    def load(self) -> list[AuditedRow]:
        from app.services.url_analyzer import InvalidURLError, normalize

        rows: list[AuditedRow] = []
        seen: set[str] = set()
        malformed = 0
        null = 0

        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            for record in csv.DictReader(handle):
                url = (record.get("URL") or "").strip()
                raw_label = (record.get("label") or "").strip()
                if not url or not raw_label:
                    null += 1
                    continue
                try:
                    parsed = normalize(url)
                except InvalidURLError:
                    malformed += 1
                    continue
                key = parsed.normalized.lower()
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    AuditedRow(
                        url=url,
                        normalized=parsed.normalized,
                        label=self.semantics.normalize(int(raw_label)),
                        registered_domain=parsed.registered_domain or parsed.hostname,
                        scheme=parsed.scheme,
                        hostname=parsed.hostname,
                        uses_https=parsed.uses_https,
                        source=self.corpus,
                    )
                )
        self._malformed = malformed
        self._null = null
        return rows

    def context(self) -> dict[str, object]:
        return {
            "label_orientation": self.semantics.orientation,
            "malformed": getattr(self, "_malformed", 0),
            "null_rows": getattr(self, "_null", 0),
            "raw_rows": getattr(self, "_raw_rows", 0),
        }


# ====================================================================
# MUD 2026
# ====================================================================

# MUD is four-class and textual, so orientation is resolved from the
# class NAMES rather than from integers — which is the safe path.
MUD_SEMANTICS = LabelSemantics(
    corpus="mud2026",
    zero_means="phishing (when mapped from the textual class 'phishing')",
    one_means="legitimate (when mapped from the textual class 'benign')",
    orientation=1,
    documented_source=(
        "MUD 2026 ships textual class_label values: benign / defacement / "
        "phishing / malware. Mapping is explicit, so no numeric inference "
        "is required."
    ),
)

# Only these two classes are commensurable with a phishing-vs-legitimate
# task. defacement and malware are DIFFERENT threat models.
MUD_INCLUDED = {"benign": LEGITIMATE, "phishing": PHISHING}
MUD_EXCLUDED = {"defacement", "malware"}


class MUD2026Adapter(CorpusAdapter):
    """Malicious URL Detection Dataset Enhanced 2026 (Kaggle).

    Four-class corpus. Only benign and phishing rows are loaded; the
    exclusion is counted and reported rather than applied silently.
    """

    corpus = "mud2026"
    semantics = MUD_SEMANTICS

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (RAW / "MUD_malicious_urls_2026_V2.csv")

    def load(self) -> list[AuditedRow]:
        from app.services.url_analyzer import InvalidURLError, normalize

        rows: list[AuditedRow] = []
        seen: set[str] = set()
        self._excluded: Counter[str] = Counter()
        malformed = 0
        duplicates = 0
        null = 0
        total = 0

        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            for record in csv.DictReader(handle):
                total += 1
                token = (record.get("class_label") or "").strip().lower()
                url = (record.get("url") or "").strip()
                if not url:
                    null += 1
                    continue
                if token not in MUD_INCLUDED:
                    self._excluded[token or "<empty>"] += 1
                    continue
                try:
                    parsed = normalize(url)
                except InvalidURLError:
                    malformed += 1
                    continue
                key = parsed.normalized.lower()
                if key in seen:
                    duplicates += 1
                    continue
                seen.add(key)
                rows.append(
                    AuditedRow(
                        url=url,
                        normalized=parsed.normalized,
                        label=MUD_INCLUDED[token],
                        registered_domain=parsed.registered_domain or parsed.hostname,
                        scheme=parsed.scheme,
                        hostname=parsed.hostname,
                        uses_https=parsed.uses_https,
                        source=self.corpus,
                    )
                )
        self._malformed = malformed
        self._duplicates = duplicates
        self._null = null
        self._raw_rows = total
        return rows

    def context(self) -> dict[str, object]:
        return {
            "label_orientation": self.semantics.orientation,
            "textual_labels": True,
            "malformed": getattr(self, "_malformed", 0),
            "duplicates": getattr(self, "_duplicates", 0),
            "null_rows": getattr(self, "_null", 0),
            "raw_rows": getattr(self, "_raw_rows", 0),
            "excluded_by_class": dict(getattr(self, "_excluded", {})),
            "excluded_reason": (
                "defacement and malware are distinct threat classes; "
                "including them as phishing would test a different target"
            ),
        }


# ====================================================================
# PHASE 2D — REALISTIC LEGITIMATE
# ====================================================================
#
# ealvaradob/phishing-dataset on HuggingFace (Apache-2.0), mirrored to
# datasets/raw/phase2d/hf_phishing_urls.json. 835,697 records, each
# {"text": <url>, "label": 0|1}.
#
# Label semantics are stated, not inferred. The dataset card declares
# "all records are labeled as 1 (Phishing) or 0 (Benign)", so the
# orientation is +1 and textual tokens 'benign'/'phishing' appear in
# the semantics block below.
#
# The reason this corpus exists is structural, and the reason is NOT
# that it has more rows. PhiUSIIL's legitimate class is 0% path-bearing
# across 134,850 URLs. This corpus measures 87.58% for the legitimate
# class and 11.78% with a query string, which is what legitimate
# traffic actually looks like. Row count is irrelevant; path
# representation is the point.
REALISTIC_SEMANTICS = LabelSemantics(
    corpus="realistic",
    zero_means="benign (legitimate)",
    one_means="phishing",
    orientation=1,
    documented_source=(
        "HuggingFace dataset card for ealvaradob/phishing-dataset: "
        "'all records are labeled as 1 (Phishing) or 0 (Benign)'."
    ),
)


class RealisticLegitimateAdapter(CorpusAdapter):
    """Realistic legitimate (and comparison phishing) URLs from HF.

    The file is a JSON array, not CSV, and many rows carry no scheme
    ('indiadaily.com/bolly_archive.htm'). Rows are prefixed with
    http:// before normalization and counted, because silently dropping
    them would bias the corpus toward whatever URLs happen to be
    fully qualified.

    Sampling is opt-in via `max_rows`. The full file is 835,697 rows;
    the experiment needs a few tens of thousands per class, and
    loading all of it to keep 80,000 wastes minutes per iteration.
    """

    corpus = "realistic"
    semantics = REALISTIC_SEMANTICS

    def __init__(
        self,
        path: Path | None = None,
        *,
        max_rows: int | None = None,
    ) -> None:
        self.path = path or (RAW / "phase2d" / "hf_phishing_urls.json")
        self.max_rows = max_rows

    def load(self) -> list[AuditedRow]:
        import json

        from app.services.url_analyzer import InvalidURLError, normalize

        records = json.loads(self.path.read_text(encoding="utf-8"))

        rows: list[AuditedRow] = []
        seen: set[str] = set()
        self._malformed = 0
        self._null = 0
        self._duplicates = 0
        self._schemeless = 0
        self._raw_rows = len(records)
        self._class_counts: Counter = Counter()

        for record in records:
            url = str(record.get("text") or "").strip()
            raw_label = record.get("label")
            if not url or raw_label is None:
                self._null += 1
                continue

            # Counted, not assumed: a schemeless row is still a
            # perfectly good URL, it just needs a scheme before the
            # parser will accept it.
            if not url.startswith(("http://", "https://")):
                url = "http://" + url
                self._schemeless += 1

            try:
                parsed = normalize(url)
            except InvalidURLError:
                self._malformed += 1
                continue

            key = parsed.normalized.lower()
            if key in seen:
                self._duplicates += 1
                continue
            seen.add(key)

            # semantics.normalize(1) == PHISHING, normalize(0) ==
            # LEGITIMATE, because orientation is +1. The map goes
            # through the dataclass rather than being hard-coded, so
            # changing the declared orientation changes behaviour.
            label = self.semantics.normalize(int(raw_label))
            self._class_counts[label] += 1

            rows.append(
                AuditedRow(
                    url=url,
                    normalized=parsed.normalized,
                    label=label,
                    registered_domain=parsed.registered_domain or parsed.hostname,
                    scheme=parsed.scheme,
                    hostname=parsed.hostname,
                    uses_https=parsed.uses_https,
                    source=self.corpus,
                )
            )

            if self.max_rows and len(rows) >= self.max_rows:
                break

        return rows

    def context(self) -> dict[str, object]:
        return {
            "label_orientation": self.semantics.orientation,
            "malformed": getattr(self, "_malformed", 0),
            "duplicates": getattr(self, "_duplicates", 0),
            "null_rows": getattr(self, "_null", 0),
            "raw_rows": getattr(self, "_raw_rows", 0),
            # This corpus carries a legitimate class that is meant to be
            # trained on, so C13-C18 apply and are BLOCKING.
            "legitimate_corpus": True,
            "schemeless_prefixed": getattr(self, "_schemeless", 0),
            "class_counts": {
                "legitimate": getattr(self, "_class_counts", Counter()).get(LEGITIMATE, 0),
                "phishing": getattr(self, "_class_counts", Counter()).get(PHISHING, 0),
            },
        }


# ====================================================================
# PHASE 2D — PHISHTANK
# ====================================================================
#
# PhishTank's "online-valid" feed is the highest-confidence phishing
# source available without registration: rows are human-verified AND
# currently online, so there is no dead-domain confound.
#
# There is no label column at all. Every row is phishing by
# construction, which is a stronger claim than any numeric encoding, so
# the semantics are declared with orientation +1 and a synthetic
# all-ones label rather than inferred from data.
PHISHTANK_SEMANTICS = LabelSemantics(
    corpus="phishtank",
    zero_means="never emitted — the feed contains phishing rows only",
    one_means="phishing",
    orientation=1,
    documented_source=(
        "PhishTank data feed documentation: 'online-valid.csv' contains "
        "only verified phishing URLs that were online at the time of "
        "export. There is no legitimate class in this feed."
    ),
)


class PhishTankAdapter(CorpusAdapter):
    """PhishTank online-valid: verified, currently-online phishing.

    Filters on `verified == yes` AND `online == yes`. Both columns are
    checked rather than trusted: the feed's header guarantees the
    shape, but a row that failed either test would be unverified or
    dead, and a dead phishing URL is a poor training example because
    its features reflect a parked page rather than a live lure.
    """

    corpus = "phishtank"
    semantics = PHISHTANK_SEMANTICS

    def __init__(
        self,
        path: Path | None = None,
        *,
        max_rows: int | None = None,
    ) -> None:
        self.path = path or (RAW / "phase2d" / "phishtank_online_valid.csv")
        self.max_rows = max_rows

    def load(self) -> list[AuditedRow]:
        from app.services.url_analyzer import InvalidURLError, normalize

        rows: list[AuditedRow] = []
        seen: set[str] = set()
        self._malformed = 0
        self._null = 0
        self._duplicates = 0
        self._unverified = 0
        self._offline = 0
        self._raw_rows = 0

        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            for record in csv.DictReader(handle):
                self._raw_rows += 1

                if (record.get("verified") or "").strip().lower() != "yes":
                    self._unverified += 1
                    continue
                if (record.get("online") or "").strip().lower() != "yes":
                    self._offline += 1
                    continue

                url = (record.get("url") or "").strip()
                if not url:
                    self._null += 1
                    continue

                try:
                    parsed = normalize(url)
                except InvalidURLError:
                    self._malformed += 1
                    continue

                key = parsed.normalized.lower()
                if key in seen:
                    self._duplicates += 1
                    continue
                seen.add(key)

                rows.append(
                    AuditedRow(
                        url=url,
                        normalized=parsed.normalized,
                        # Every surviving row is phishing. Written as the
                        # constant PHISHING rather than read from a
                        # column, because there IS no column.
                        label=PHISHING,
                        registered_domain=parsed.registered_domain or parsed.hostname,
                        scheme=parsed.scheme,
                        hostname=parsed.hostname,
                        uses_https=parsed.uses_https,
                        source=self.corpus,
                    )
                )

                if self.max_rows and len(rows) >= self.max_rows:
                    break

        return rows

    def context(self) -> dict[str, object]:
        return {
            "label_orientation": self.semantics.orientation,
            "textual_labels": True,
            "malformed": getattr(self, "_malformed", 0),
            "duplicates": getattr(self, "_duplicates", 0),
            "null_rows": getattr(self, "_null", 0),
            "raw_rows": getattr(self, "_raw_rows", 0),
            "unverified_rows": getattr(self, "_unverified", 0),
            "offline_rows": getattr(self, "_offline", 0),
            # Phishing-only: C13-C18 describe the LEGITIMATE class and
            # would be vacuous here. They are explicitly not run rather
            # than run and reported as passing by accident.
            "legitimate_corpus": False,
        }


# ====================================================================
# PHASE 2E — HTTPS-REALISTIC LEGITIMATE
# ====================================================================
#
# Mendeley Data, "Phishing URL dataset" (legitimate subset), mirrored to
# datasets/raw/phase2d/mendeley_legit_urls.txt. 345,738 URLs, CC BY 4.0,
# one URL per line, no label column at all.
#
# WHY A SEPARATE ADAPTER AND NOT A REUSE OF RealisticLegitimateAdapter
# -------------------------------------------------------------------
# Both are "legitimate URLs harvested from the web", and both are
# upstream-labelled rather than human-verified. But they differ in the
# one dimension Phase 2E cares about:
#
#   realistic   schemeless host+path rows, prefixed http://, mixed scheme
#   mendeley    99.99% HTTPS, 85.04% with a path, 13.29% with a query
#
# Mendeley is therefore the scheme-realistic half of the legitimate
# class and `realistic` is the path-realistic half. Sharing one adapter
# would have hidden exactly the difference the Phase 2E experiment
# exists to measure, which is the whole reason adapters declare
# semantics instead of sharing a loader.
#
# LABEL SEMANTICS. There is no label column. Every row is legitimate BY
# CONSTRUCTION of the file being the benign subset of a phishing
# dataset — the same claim PhishTank makes, but with weaker evidence,
# because PhishTank verifies each URL individually and nobody verified
# these. The orientation is +1 so that the synthetic label routes
# through the same `semantics.normalize` path as every other corpus.
#
# WHAT THIS CORPUS IS NOT. It adds HTTPS realism and scheme shape. It
# does NOT add domain diversity: measured against the corpora already
# in hand, 95.3% of its registered domains also appear in mud2026 and
# 95.9% in realistic. Any generalisation gain from this source must
# therefore come from the SCHEME distribution, and Phase 2E measures
# that rather than assuming it.
HTTPS_REALISTIC_SEMANTICS = LabelSemantics(
    corpus="https_realistic",
    zero_means="never emitted — the file is the legitimate subset only",
    one_means="legitimate",
    orientation=1,
    documented_source=(
        "Mendeley Data dataset vfszbj9b36: the file is the benign/legitimate "
        "subset of the published phishing URL dataset. There is no label "
        "column; legitimacy is asserted by file membership, not verified "
        "per row."
    ),
)


class HTTPSRealisticAdapter(CorpusAdapter):
    """Mendeley legitimate subset: the HTTPS-realistic legitimate half.

    `per_domain_cap` is applied at LOAD time rather than after loading,
    which matters for a 345k-row file: capping before the rows reach
    memory keeps the working set at the capped size instead of holding
    345,738 AuditedRow objects to discard most of them. The cap is
    deterministic — the first `per_domain_cap` URLs seen for a domain
    survive, in file order — so a rerun reproduces the corpus exactly
    without a random seed, and the choice is auditable against the
    source file.

    The cap exists because the source's ten largest domains contribute
    17.68% of all rows (wikipedia 12,895, youtube 8,627, facebook
    8,275, blogspot 7,036). Uncapped, the largest domain alone supplies
    one row in twenty-seven, and a model trained on that learns three
    popular websites rather than legitimate URL structure. Which cap to
    use is decided by Phase 2E on measured generalisation, not by which
    cap retains the most rows.
    """

    corpus = "https_realistic"
    semantics = HTTPS_REALISTIC_SEMANTICS

    def __init__(
        self,
        path: Path | None = None,
        *,
        per_domain_cap: int | None = 25,
        max_rows: int | None = None,
    ) -> None:
        self.path = path or (RAW / "phase2d" / "mendeley_legit_urls.txt")
        self.per_domain_cap = per_domain_cap
        self.max_rows = max_rows

    def load(self) -> list[AuditedRow]:
        from app.services.url_analyzer import InvalidURLError, normalize

        rows: list[AuditedRow] = []
        seen: set[str] = set()
        per_domain: Counter = Counter()
        self._malformed = 0
        self._null = 0
        self._duplicates = 0
        self._over_cap = 0
        self._raw_rows = 0
        self._scheme: Counter = Counter()

        with self.path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                self._raw_rows += 1

                # Counted, not assumed: a schemeless row is still a
                # perfectly good URL and must not be silently dropped.
                # The source is 99.99% HTTPS, but "99.99%" is a rounded
                # claim and the remainder has to go somewhere.
                if not raw.startswith(("http://", "https://")):
                    raw = "http://" + raw

                try:
                    parsed = normalize(raw)
                except InvalidURLError:
                    self._malformed += 1
                    continue

                key = parsed.normalized.lower()
                if key in seen:
                    self._duplicates += 1
                    continue
                seen.add(key)

                domain = parsed.registered_domain or parsed.hostname
                if (
                    self.per_domain_cap is not None
                    and per_domain[domain] >= self.per_domain_cap
                ):
                    # The cap is enforced BEFORE the URL enters the row
                    # list, so the returned corpus is capped by
                    # construction rather than capped after the fact.
                    # C22 re-derives the bound from these rows and can
                    # only fail if that claim is wrong.
                    self._over_cap += 1
                    continue

                per_domain[domain] += 1
                self._scheme[parsed.scheme] += 1

                rows.append(
                    AuditedRow(
                        url=raw,
                        normalized=parsed.normalized,
                        # Route the synthetic label through the declared
                        # semantics rather than hard-coding LEGITIMATE,
                        # so a change to the declared orientation changes
                        # behaviour instead of being silently ignored.
                        label=self.semantics.normalize(0),
                        registered_domain=domain,
                        scheme=parsed.scheme,
                        hostname=parsed.hostname,
                        uses_https=parsed.uses_https,
                        source=self.corpus,
                    )
                )

                if self.max_rows and len(rows) >= self.max_rows:
                    break

        return rows

    def context(self) -> dict[str, object]:
        return {
            "label_orientation": self.semantics.orientation,
            "textual_labels": True,
            "malformed": getattr(self, "_malformed", 0),
            "duplicates": getattr(self, "_duplicates", 0),
            "null_rows": getattr(self, "_null", 0),
            "raw_rows": getattr(self, "_raw_rows", 0),
            # Carries a legitimate class intended for training, so
            # C13-C18 and C19-C21 apply.
            "legitimate_corpus": True,
            "per_domain_cap": self.per_domain_cap,
            "rows_dropped_by_cap": getattr(self, "_over_cap", 0),
            "scheme_distribution": dict(getattr(self, "_scheme", {})),
            "https_rows": getattr(self, "_scheme", Counter())["https"],
        }


# ====================================================================
# REGISTRY
# ====================================================================

ADAPTERS: dict[str, type[CorpusAdapter]] = {
    "phiusil": PhiUSIILAdapter,
    "mud2026": MUD2026Adapter,
    "realistic": RealisticLegitimateAdapter,
    "https_realistic": HTTPSRealisticAdapter,
    "phishtank": PhishTankAdapter,
}

# Which corpora carry a legitimate class. Used by the Phase 2D runner to
# decide where the C13-C18 blocking checks apply.
LEGITIMATE_CORPORA = frozenset(
    {"phiusil", "mud2026", "realistic", "https_realistic"}
)


def load_corpus(
    name: str, **adapter_kwargs: object
) -> tuple[list[AuditedRow], dict[str, object]]:
    """Load a corpus by name, returning rows and gate context.

    `adapter_kwargs` are forwarded to the adapter constructor, so a
    caller can ask for a specific per-domain cap without a bespoke
    registry entry. Phase 2E uses this to sweep caps 25/50/100 through
    the one registered adapter.
    """
    if name not in ADAPTERS:
        raise KeyError(
            f"Unknown corpus {name!r}. Registered: {sorted(ADAPTERS)}. "
            f"Add a CorpusAdapter subclass to extend this."
        )
    adapter = ADAPTERS[name](**adapter_kwargs)  # type: ignore[arg-type]
    rows = adapter.load()
    return rows, adapter.context()


def semantics_summary() -> dict[str, dict[str, object]]:
    """Every adapter's declared label meaning, for the audit report."""
    return {name: cls.semantics.to_dict() for name, cls in ADAPTERS.items()}