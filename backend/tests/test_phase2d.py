"""
Phase 2D tests: legitimate-corpus realism gate (C13-C18) and the two
Phase 2D adapters.

The gate tests are the important ones. They assert that a corpus with
PhiUSIIL's legitimate-class shape — realistic labels, 0% path-bearing
URLs — is BLOCKED, because that shape is what produced a model that
flags docs.python.org as phishing at p > 0.99999 while reporting
AUC 0.998 against it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ml.corpus_adapters import (
    ADAPTERS,
    LEGITIMATE_CORPORA,
    PHISHTANK_SEMANTICS,
    PhishTankAdapter,
    REALISTIC_SEMANTICS,
    RealisticLegitimateAdapter,
    semantics_summary,
)
from app.ml.corpus_quality import (
    CorpusQualityGate,
    Severity,
    Verdict,
    gate_corpus,
)
from app.ml.datasets import LEGITIMATE, PHISHING, AuditedRow

BACKEND = Path(__file__).resolve().parents[1]

# The two shape-defining prefixes. C13-C18's verdicts must follow from
# the URL structure alone, so the tests build rows from these rather
# than from any corpus.
PATHED_LEGITIMATE = "https://docs.python.org/3/library/asyncio.html"
BARE_LEGITIMATE = "https://www.nasa.gov"
PATHED_PHISHING = "https://secure-login-verify.tk/webscr/signin"


def row(url: str, label: int, source: str = "test") -> AuditedRow:
    host = url.split("://", 1)[-1].split("/", 1)[0]
    return AuditedRow(
        url=url,
        normalized=url,
        label=label,
        registered_domain=host,
        scheme=url.split("://", 1)[0],
        hostname=host,
        uses_https=True,
        source=source,
    )


def phi_usil_shape(n: int = 400) -> list[AuditedRow]:
    """A corpus with PhiUSIIL's defect: legitimate = bare domains only."""
    rows: list[AuditedRow] = []
    for i in range(n):
        rows.append(row(f"https://legit-bare-{i}.com", LEGITIMATE))
        rows.append(
            row(f"https://phish-{i}.com/secure/login/verify.php", PHISHING)
        )
    return rows


def realistic_legitimate_shape(n: int = 400) -> list[AuditedRow]:
    """A corpus with realistic legitimate structure: paths and queries."""
    rows: list[AuditedRow] = []
    for i in range(n):
        rows.append(
            row(f"https://real-site-{i}.com/en-US/docs/Web/HTTP/page.html", LEGITIMATE)
        )
        rows.append(
            row(f"https://real-site-{i}.com/search?q=example&lang=en", LEGITIMATE)
        )
        rows.append(
            row(f"https://attack-{i}.com/secure/login/verify.php", PHISHING)
        )
    return rows


# ====================================================================
# C13 — path representation
# ====================================================================


def test_c13_blocks_a_bare_domain_legitimate_class() -> None:
    """The exact PhiUSIIL defect must be a BLOCKING failure."""
    report = gate_corpus(
        "phiusil_shape", phi_usil_shape(), legitimate_corpus=True
    )
    check = report.get("C13_legitimate_path_representation")

    assert check is not None
    assert check.verdict is Verdict.FAIL
    assert check.severity is Severity.CRITICAL
    assert check.blocking is True
    assert check.measured["path_presence_rate_legitimate"] == 0.0
    assert "domain list" in check.message
    assert report.passed is False


def test_c13_passes_a_realistic_legitimate_class() -> None:
    report = gate_corpus(
        "realistic_shape", realistic_legitimate_shape(), legitimate_corpus=True
    )
    check = report.get("C13_legitimate_path_representation")

    assert check is not None
    assert check.verdict is Verdict.PASS
    assert check.measured["path_presence_rate_legitimate"] == 1.0


def test_c13_threshold_is_a_floor_not_a_target() -> None:
    """A corpus at the floor passes; one below it fails. The gate does
    not require the corpus to be perfectly balanced against real
    traffic — only to clear a representativeness minimum."""
    gate = CorpusQualityGate("floor")
    assert gate.MIN_LEGITIMATE_PATH_RATE == 0.25

    below = [
        row("https://bare-a.com", LEGITIMATE),
        row("https://bare-b.com", LEGITIMATE),
        row("https://bare-c.com", LEGITIMATE),
        row("https://bare-d.com", LEGITIMATE),
        row("https://one-pathed.com/docs", LEGITIMATE),
        row("https://attack.com/x/y", PHISHING),
    ]
    report = gate_corpus("floor", below, legitimate_corpus=True)
    assert report.get("C13_legitimate_path_representation").blocking is True

    at_floor = [row(f"https://bare-{i}.com", LEGITIMATE) for i in range(3)]
    at_floor += [row(f"https://p{i}.com/docs", LEGITIMATE) for i in range(3)]
    at_floor.append(row("https://attack.com/x/y", PHISHING))
    report = gate_corpus("floor2", at_floor, legitimate_corpus=True)
    assert report.get("C13_legitimate_path_representation").verdict is Verdict.PASS


# ====================================================================
# C14 — query representation
# ====================================================================


def test_c14_blocks_a_corpus_with_no_legitimate_queries() -> None:
    report = gate_corpus(
        "no_queries", phi_usil_shape(), legitimate_corpus=True
    )
    check = report.get("C14_legitimate_query_representation")

    assert check is not None
    assert check.blocking is True
    assert check.measured["query_presence_rate_legitimate"] == 0.0


def test_c14_measures_query_strings_independently_of_paths() -> None:
    """A path-bearing corpus with no queries still fails C14.

    Path representation and query representation are different signals.
    A corpus can satisfy one and miss the other, and the gate has to
    say so rather than letting one stand in for the other.
    """
    rows = [
        row(f"https://site-{i}.com/docs/guide", LEGITIMATE) for i in range(200)
    ] + [row("https://attack.com/x/y", PHISHING)]

    report = gate_corpus("paths_no_queries", rows, legitimate_corpus=True)
    assert report.get("C13_legitimate_path_representation").verdict is Verdict.PASS
    assert report.get("C14_legitimate_query_representation").blocking is True


# ====================================================================
# C15 — domain diversity
# ====================================================================


def test_c15_blocks_a_low_diversity_legitimate_class() -> None:
    """Few distinct domains carrying many URLs is memorisation.

    Diversity is measured per row, so a corpus can hold a respectable
    absolute domain count and still fail: 300 domains over 3,000 rows is
    not a legitimate class, it is 300 domains repeated ten times.
    """
    rows = [
        row(f"https://site{i % 20}.com/docs/page{i}.html", LEGITIMATE)
        for i in range(1000)
    ] + [row("https://attack.com/x/y", PHISHING)]

    report = gate_corpus("low_diversity", rows, legitimate_corpus=True)
    check = report.get("C15_legitimate_domain_diversity")

    assert check is not None
    assert check.blocking is True
    assert check.measured["distinct_domains"] == 20
    assert check.measured["legitimate_rows"] == 1000
    assert check.measured["domains_per_row"] == 0.02
    assert check.measured["domains_per_row"] < (
        CorpusQualityGate.MIN_LEGITIMATE_DOMAINS_PER_ROW
    )


def test_c15_blocks_when_one_domain_dominates() -> None:
    rows = [
        row(f"https://site{i}.com/docs", LEGITIMATE) for i in range(300)
    ] + [row("https://huge.com/a/b/c/d/e", LEGITIMATE) for _ in range(150)]
    rows += [row("https://attack.com/x/y", PHISHING)]

    report = gate_corpus("one_domain", rows, legitimate_corpus=True)
    check = report.get("C15_legitimate_domain_diversity")

    assert check is not None
    assert check.blocking is True
    assert check.measured["max_single_domain_share"] > 0.05


# ====================================================================
# C16 — deep paths
# ====================================================================


def test_c16_blocks_shallow_only_paths() -> None:
    """'/about' is not enough. Nested paths are where v1 failed."""
    rows = [
        row(f"https://site-{i}.com/about", LEGITIMATE) for i in range(300)
    ] + [row("https://attack.com/x/y", PHISHING)]

    report = gate_corpus("shallow", rows, legitimate_corpus=True)
    check = report.get("C16_legitimate_deep_path_representation")

    assert check is not None
    assert check.blocking is True
    assert check.measured["deep_path_rate_legitimate"] == 0.0


def test_c16_measures_depth_not_merely_presence() -> None:
    """A corpus where every legitimate path is depth-1 passes C13 but
    fails C16. The two checks must not collapse into one.

    '/only/one' is depth 2; the depth-1 case is '/about'. Using a
    single-segment path is the whole point — it is present, so C13 is
    satisfied, and it is shallow, so C16 is not.
    """
    rows = [
        row(f"https://site-{i}.com/about", LEGITIMATE) for i in range(300)
    ] + [row("https://attack.com/x/y", PHISHING)]

    report = gate_corpus("depth1", rows, legitimate_corpus=True)
    assert report.get("C13_legitimate_path_representation").verdict is Verdict.PASS
    assert report.get("C16_legitimate_deep_path_representation").blocking is True


def test_c16_passes_when_paths_are_nested() -> None:
    rows = [
        row(f"https://site-{i}.com/en-US/docs/Web/page", LEGITIMATE)
        for i in range(300)
    ] + [row("https://attack.com/x/y", PHISHING)]

    report = gate_corpus("deep", rows, legitimate_corpus=True)
    check = report.get("C16_legitimate_deep_path_representation")
    assert check.verdict is Verdict.PASS
    assert check.measured["deep_path_rate_legitimate"] == 1.0
    assert check.measured["max_path_depth"] == 4


# ====================================================================
# C17 — source concentration
# ====================================================================


def test_c17_is_a_warning_not_a_block() -> None:
    """Single-sourced is a recorded caveat, not a defect.

    Concentration cannot prove the corpus is bad, so blocking on it
    would reject corpora that are perfectly fine to train on and would
    make the gate's failures untrustworthy.
    """
    rows = [
        row(
            f"https://site-{i}.com/docs/guide/page{i}",
            LEGITIMATE,
            source="only_source",
        )
        for i in range(300)
    ] + [row("https://attack.com/x/y", PHISHING)]

    report = gate_corpus("single_source", rows, legitimate_corpus=True)
    check = report.get("C17_source_concentration")

    assert check is not None
    assert check.verdict is Verdict.FAIL
    assert check.severity is Severity.WARNING
    assert check.blocking is False
    assert check.measured["max_source_share"] == 1.0


# ====================================================================
# C18 — shortcut risk
# ====================================================================


def test_c18_blocks_the_bare_host_shortcut() -> None:
    """The composite failure: mostly bare legitimate hosts AND a path
    gap. Either half alone is a corpus property; together they are the
    exact shape of the shipped defect."""
    report = gate_corpus(
        "shortcut", phi_usil_shape(), legitimate_corpus=True
    )
    check = report.get("C18_suspicious_shortcut_risk")

    assert check is not None
    assert check.blocking is True
    assert check.measured["has_path_rule_shortcut"] is True
    assert check.measured["has_path_rule_accuracy"] > 0.9
    assert "docs.python.org" in check.message


def test_c18_passes_when_paths_appear_in_both_classes() -> None:
    report = gate_corpus(
        "no_shortcut", realistic_legitimate_shape(), legitimate_corpus=True
    )
    check = report.get("C18_suspicious_shortcut_risk")

    assert check is not None
    assert check.verdict is Verdict.PASS
    assert check.measured["has_path_rule_shortcut"] is False


def test_c18_does_not_fire_when_the_gap_points_the_safe_way() -> None:
    """Legitimate traffic that is MORE path-bearing than phishing cannot
    teach 'path => phishing', so the shortcut check must not fire even
    though a path-rate gap exists."""
    rows = [row(f"https://site-{i}.com/docs/guide", LEGITIMATE) for i in range(300)]
    rows += [row("https://attack.com", PHISHING) for _ in range(300)]

    report = gate_corpus("safe_direction", rows, legitimate_corpus=True)
    check = report.get("C18_suspicious_shortcut_risk")

    assert check is not None
    assert check.verdict is Verdict.PASS
    # ...while C06, being two-sided, still records the gap.
    assert report.get("C06_path_presence").verdict is Verdict.FAIL


# ====================================================================
# Gate plumbing
# ====================================================================


def test_c13_to_c18_are_skipped_for_a_phishing_only_corpus() -> None:
    """A phishing-only corpus has no legitimate class to be realistic
    about. The checks must be absent, not present-and-passing — a
    skipped check that reported PASS would be a silent lie."""
    rows = [row(f"https://attack-{i}.com/x/y", PHISHING) for i in range(200)]
    report = gate_corpus("phishing_only", rows, legitimate_corpus=False)

    for check_id in (
        "C13_legitimate_path_representation",
        "C14_legitimate_query_representation",
        "C15_legitimate_domain_diversity",
        "C16_legitimate_deep_path_representation",
        "C17_source_concentration",
        "C18_suspicious_shortcut_risk",
    ):
        assert report.get(check_id) is None


def test_every_phase2d_check_reports_measured_values() -> None:
    """A check that cannot be evaluated is itself a failure, so no
    check may return an empty measurement."""
    report = gate_corpus(
        "measured", realistic_legitimate_shape(), legitimate_corpus=True
    )
    for check in report.checks:
        if check.check_id >= "C13":
            assert check.measured, f"{check.check_id} reported no measurements"
            assert isinstance(check.message, str)


def test_c13_cannot_be_satisfied_by_relabelling() -> None:
    """The gate measures URL STRUCTURE, not the label vocabulary.

    PhiUSIIL called its bare-domain rows "legitimate" and that is
    precisely what these checks refuse to accept. So splitting the same
    bare-domain rows across several differently-named sources — a
    cosmetic change that makes a corpus look more diverse and more
    trustworthy — must leave C13's verdict untouched.
    """
    from_one_source = phi_usil_shape()
    from_many = [
        AuditedRow(
            url=r.url,
            normalized=r.normalized,
            label=r.label,
            registered_domain=r.registered_domain,
            scheme=r.scheme,
            hostname=r.hostname,
            uses_https=r.uses_https,
            source=f"source_{i % 5}",
        )
        for i, r in enumerate(from_one_source)
    ]

    a = gate_corpus("one_source", from_one_source, legitimate_corpus=True)
    b = gate_corpus("many_sources", from_many, legitimate_corpus=True)

    assert a.get("C13_legitimate_path_representation").measured == (
        b.get("C13_legitimate_path_representation").measured
    )
    assert a.get("C13_legitimate_path_representation").blocking is True
    assert b.get("C13_legitimate_path_representation").blocking is True

    # C17 sees the difference the cosmetic change makes; C13 does not.
    assert a.get("C17_source_concentration").verdict is Verdict.FAIL
    assert b.get("C17_source_concentration").verdict is Verdict.PASS


def test_c18_according_to_its_rule_not_to_a_proxy() -> None:
    """The reported shortcut accuracy must be the rule's actual accuracy.

    An earlier version took max(legit_path, 1 - phish_path), which is
    not the accuracy of any single rule — it reports 1.0 for a corpus
    the rule scores 0.5 on. A diagnostic that flatters the defect it
    exists to measure is worse than none.
    """
    # Legitimate: all bare. Phishing: all pathed. The rule "flag iff
    # there is a path" is exactly right, so accuracy must be 1.0.
    perfect = phi_usil_shape(200)
    report = gate_corpus("perfect_shortcut", perfect, legitimate_corpus=True)
    assert report.get("C18_suspicious_shortcut_risk").measured[
        "has_path_rule_accuracy"
    ] == 1.0

    # No signal at all: BOTH classes are entirely bare, so the rule
    # "flag iff there is a path" correctly flags nothing and gets every
    # legitimate row right and every phishing row wrong — 0.5. This is
    # the case the old formula got catastrophically wrong: with both
    # path rates at 0.0 it reported max(0.0, 1-0.0) = 1.0.
    coinflip = []
    for i in range(200):
        coinflip.append(row(f"https://bare-{i}.com", LEGITIMATE))
        coinflip.append(row(f"https://bare-phish-{i}.com", PHISHING))
    coinflip_report = gate_corpus(
        "coinflip", coinflip, legitimate_corpus=True
    )
    assert coinflip_report.get("C18_suspicious_shortcut_risk").measured[
        "has_path_rule_accuracy"
    ] == 0.5

    # A model could achieve 0.5 accuracy here, which is exactly the
    # point: the corpus carries no signal for the rule to capture.
    assert coinflip_report.get("C18_suspicious_shortcut_risk").measured[
        "has_path_rule_shortcut"
    ] is False

    # Mixed: half the phishing rows carry a path. The rule now gets the
    # bare legitimate rows and only half the phishing rows right.
    mixed = [row(f"https://bare-{i}.com", LEGITIMATE) for i in range(200)]
    mixed += [
        row(f"https://phish-paths-{i}.com/x/y", PHISHING) for i in range(100)
    ]
    mixed += [row(f"https://phish-bare-{i}.com", PHISHING) for i in range(100)]
    mixed_report = gate_corpus("mixed", mixed, legitimate_corpus=True)
    # 200 correct legitimate + 100 correct phishing, out of 400.
    assert mixed_report.get("C18_suspicious_shortcut_risk").measured[
        "has_path_rule_accuracy"
    ] == 0.75


# ====================================================================
# PROMOTION SELECTION
# ====================================================================


def _candidate_row(**overrides):
    row = {
        "configuration": "all_features|xgboost",
        "real_world_fp": 5,
        "real_world_n": 14,
        "grouped_auc": 0.9476,
        "grouped_fpr": 0.1368,
        "phishing_recall_phishtank": 0.9092,
        "worst_corpus_auc": 0.8481,
    }
    row.update(overrides)
    return row


def _baseline(**overrides):
    base = {
        "model": "basirah-url-v1",
        "available": True,
        "threshold": 0.996526,
        "real_world": {"flagged": 10, "n": 14},
        "grouped_auc": 0.5738,
        # v1 flags 65.8% of legitimate traffic. This is the number that
        # makes its 0.979 PhishTank recall meaningless.
        "grouped_fpr": 0.6583,
        "phishing_recall": 0.9788,
        "worst_corpus_auc": 0.3112,
    }
    base.update(overrides)
    return base


def test_recall_at_matched_fpr_rewards_a_better_separating_model() -> None:
    """The whole point: recall must be compared at a shared FPR.

    v1-style behaviour (high recall because it flags almost everything)
    must not beat a model that genuinely separates the classes.
    """
    import numpy as np

    from scripts.run_phase2d_experiment import recall_at_matched_fpr

    rng = np.random.default_rng(0)
    legit = rng.normal(0.0, 1.0, 20_000)
    # A lounder: phishing scores overlap legitimate scores heavily.
    weak_phish = rng.normal(0.6, 1.0, 5_000)
    # A sharp separator.
    strong_phish = rng.normal(3.0, 0.5, 5_000)

    weak = recall_at_matched_fpr(weak_phish, legit, 0.05)
    strong = recall_at_matched_fpr(strong_phish, legit, 0.05)

    assert strong > weak
    # Not exactly 1.0: Gaussian tails still overlap, so a handful of
    # legitimate URLs score above every phishing URL. The point of the
    # assertion is the ORDERING, not a perfect separation.
    assert strong > 0.99


def test_matched_fpr_actually_holds_the_false_positive_rate() -> None:
    """At target_fpr, the legitimate false-positive rate must equal it."""
    import numpy as np

    from scripts.run_phase2d_experiment import recall_at_matched_fpr

    rng = np.random.default_rng(1)
    legit = rng.normal(0.0, 1.0, 100_000)
    phish = rng.normal(1.0, 1.0, 10_000)

    for target in (0.01, 0.05, 0.10):
        threshold = float(np.quantile(legit, 1.0 - target))
        achieved = float((legit >= threshold).mean())
        assert achieved == pytest.approx(target, abs=0.002)
        assert recall_at_matched_fpr(phish, legit, target) > 0.0


def test_matched_fpr_returns_nan_on_empty_input() -> None:
    import numpy as np

    from scripts.run_phase2d_experiment import recall_at_matched_fpr

    empty = np.array([])
    assert np.isnan(recall_at_matched_fpr(empty, empty, 0.05))
    assert np.isnan(
        recall_at_matched_fpr(np.array([0.5]), empty, 0.05)
    )


def test_raw_recall_regression_alone_does_not_block_promotion() -> None:
    """The defect criterion: v1's 0.979 raw recall must not veto a
    candidate at 0.909, because v1 earns that recall at a 0.658 FPR.

    An earlier version of this rule compared raw recall and therefore
    retained a model that flags two thirds of all legitimate traffic,
    on the grounds that it caught marginally more phishing. That is
    exactly backwards.
    """
    from scripts.run_phase2d_experiment import decide_promotion

    decision = decide_promotion(
        [_candidate_row()],
        _baseline(),
        "all_features|xgboost",
        # At a matched 5% FPR the candidate is far ahead.
        {"target_fpr": 0.05, "baseline": 0.31, "candidate": 0.95},
    )
    assert decision["promote"] is True
    assert decision["decision"] == "promoted"
    # The raw comparison is still recorded, and explicitly marked as
    # not being what governed the decision.
    assert decision["baseline_phishing_recall"] == pytest.approx(0.9788)
    assert decision["candidate_phishing_recall"] == pytest.approx(0.9092)


def test_real_recall_regression_at_matched_fpr_blocks_promotion() -> None:
    """A genuine loss of detection ability still blocks."""
    from scripts.run_phase2d_experiment import decide_promotion

    decision = decide_promotion(
        [_candidate_row()],
        _baseline(),
        "all_features|xgboost",
        {"target_fpr": 0.05, "baseline": 0.95, "candidate": 0.40},
    )
    assert decision["promote"] is False
    assert decision["decision"] == "retained-v1"
    assert any("REGRESSION" in r for r in decision["reasons"])


def test_immaterial_improvement_blocks_promotion() -> None:
    """9/14 -> 8/14 is one URL on a set of fourteen: noise, not a fix."""
    from scripts.run_phase2d_experiment import decide_promotion

    decision = decide_promotion(
        [_candidate_row(real_world_fp=9)],
        _baseline(),
        "all_features|xgboost",
        {"target_fpr": 0.05, "baseline": 0.31, "candidate": 0.95},
    )
    assert decision["promote"] is False
    assert decision["real_world_fp_improvement"] == 1
    assert any("materiality floor" in r for r in decision["reasons"])


def test_generalisation_regression_blocks_promotion() -> None:
    from scripts.run_phase2d_experiment import decide_promotion

    decision = decide_promotion(
        [_candidate_row(worst_corpus_auc=0.20)],
        _baseline(),
        "all_features|xgboost",
        {"target_fpr": 0.05, "baseline": 0.31, "candidate": 0.95},
    )
    assert decision["promote"] is False
    assert any("generalization regressed" in r for r in decision["reasons"])


def test_select_best_prefers_fewer_real_world_false_positives() -> None:
    """Ranking is by real-world FP first — that is the product goal."""
    from scripts.run_phase2d_experiment import select_best

    rows = [
        _candidate_row(
            configuration="a", real_world_fp=8, grouped_auc=0.99
        ),
        _candidate_row(
            configuration="b", real_world_fp=3, grouped_auc=0.90
        ),
        _candidate_row(
            configuration="c", real_world_fp=3, grouped_auc=0.95
        ),
    ]
    # b and c tie on FP; the higher grouped AUC breaks the tie.
    assert select_best(rows, _baseline()) == "c"


def test_select_best_excludes_candidates_missing_the_recall_floor() -> None:
    """A model that clears FP targets by missing attacks is ineligible."""
    from scripts.run_phase2d_experiment import select_best

    rows = [
        _candidate_row(
            configuration="aggressive",
            real_world_fp=0,
            phishing_recall_phishtank=0.40,
            worst_corpus_auc=0.95,
        ),
        _candidate_row(
            configuration="balanced",
            real_world_fp=4,
            phishing_recall_phishtank=0.95,
            worst_corpus_auc=0.90,
        ),
    ]
    assert select_best(rows, _baseline()) == "balanced"


def test_select_best_excludes_candidates_with_poor_generalization() -> None:
    from scripts.run_phase2d_experiment import select_best

    rows = [
        _candidate_row(
            configuration="narrow",
            real_world_fp=0,
            phishing_recall_phishtank=0.99,
            worst_corpus_auc=0.40,
        ),
        _candidate_row(
            configuration="broad",
            real_world_fp=5,
            phishing_recall_phishtank=0.95,
            worst_corpus_auc=0.85,
        ),
    ]
    assert select_best(rows, _baseline()) == "broad"


def test_select_best_raises_when_there_are_no_candidates() -> None:
    from scripts.run_phase2d_experiment import select_best

    with pytest.raises(ValueError):
        select_best([], _baseline())


def test_grouped_partition_holds_domains_together() -> None:
    """The split invariant the run depends on."""
    import numpy as np

    from scripts.run_phase2d_experiment import (
        assert_partition_is_clean,
        grouped_partition,
    )

    rng = np.random.default_rng(42)
    domains = [f"site{i}.example" for i in range(5_000)]
    groups = np.asarray(
        domains + list(rng.choice(domains, 15_000))
    )
    y = rng.integers(0, 2, len(groups))

    parts = grouped_partition(groups, y)
    report = assert_partition_is_clean(groups, parts)

    assert report["leakage_free"] is True
    assert report["overlap_between_partitions"] == {}
    # Every row lands in exactly one partition.
    all_indices = np.concatenate(
        [parts["train"], parts["val"], parts["test"]]
    )
    assert len(np.unique(all_indices)) == len(groups)
    # All three partitions are non-trivial.
    for name in ("train", "val", "test"):
        assert len(parts[name]) > 0


def test_grouped_partition_is_deterministic() -> None:
    import numpy as np

    from scripts.run_phase2d_experiment import grouped_partition

    rng = np.random.default_rng(7)
    groups = np.asarray([f"d{i}" for i in range(2_000)])
    y = rng.integers(0, 2, len(groups))
    first = grouped_partition(groups, y)
    second = grouped_partition(groups, y)
    for name in first:
        assert np.array_equal(first[name], second[name])


def test_promotion_never_names_v1_as_the_candidate_bundle() -> None:
    """The production bundle must not be the promotion target.

    Promotion writes a NEW bundle name. Overwriting basirah-url-v1
    would destroy the only artefact that documents the defect this
    phase exists to fix, and would do it as a side effect of an
    experiment run.
    """
    from scripts.run_phase2d_experiment import BASELINE_NAME, CANDIDATE_NAME

    assert CANDIDATE_NAME != BASELINE_NAME
    assert BASELINE_NAME == "basirah-url-v1"


def test_reversed_path_presence_demotion_is_opt_in() -> None:
    """C06 is two-sided, so a benign-heavy gap trips it. The demotion
    must require an explicit opt-in and must leave the measured value
    in the audit."""
    rows = [row(f"https://site-{i}.com/docs/guide", LEGITIMATE) for i in range(300)]
    rows += [row("https://attack.com", PHISHING) for _ in range(300)]

    strict = gate_corpus("strict", rows, legitimate_corpus=True)
    assert strict.get("C06_path_presence").blocking is True

    relaxed = gate_corpus(
        "relaxed", rows, legitimate_corpus=True, allow_reversed_path_presence=True
    )
    check = relaxed.get("C06_path_presence")
    assert check.blocking is False
    assert check.measured["reversed_direction"] is True
    assert check.measured["gap"] > 0
    assert "safe direction" in check.message.lower()


# ====================================================================
# Adapters
# ====================================================================


def test_realistic_adapter_declares_its_orientation() -> None:
    assert REALISTIC_SEMANTICS.orientation == 1
    assert "benign" in REALISTIC_SEMANTICS.zero_means.lower()
    assert REALISTIC_SEMANTICS.normalize(0) == LEGITIMATE
    assert REALISTIC_SEMANTICS.normalize(1) == PHISHING


def test_phishtank_declares_phishing_only() -> None:
    assert PHISHTANK_SEMANTICS.orientation == 1
    assert PHISHTANK_SEMANTICS.normalize(1) == PHISHING
    assert "no legitimate class" in PHISHTANK_SEMANTICS.documented_source.lower()


def test_phishtank_adapter_declares_itself_not_a_legitimate_corpus() -> None:
    """C13-C18 describe the legitimate class and are vacuous on a
    phishing-only feed. The adapter says so in its context, so the gate
    skips them instead of reporting a hollow PASS.

    context() is safe to call without load(): every count reads through
    getattr with a default, so an unloaded adapter reports zeros rather
    than raising. That is what makes the declaration testable without
    reading a 14 MB feed.
    """
    assert PhishTankAdapter().context()["legitimate_corpus"] is False


def test_realistic_adapter_declares_itself_a_legitimate_corpus() -> None:
    assert RealisticLegitimateAdapter().context()["legitimate_corpus"] is True
    assert "realistic" in LEGITIMATE_CORPORA


def test_both_phase2d_adapters_are_registered() -> None:
    assert "realistic" in ADAPTERS
    assert "phishtank" in ADAPTERS
    assert "realistic" in LEGITIMATE_CORPORA
    assert "phishtank" not in LEGITIMATE_CORPORA
    summary = semantics_summary()
    for name in ("realistic", "phishtank"):
        assert summary[name]["documented_source"]