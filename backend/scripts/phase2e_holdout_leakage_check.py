"""Verify the expanded holdout cannot leak, and document why it must.

The smoke run correctly aborted:

    AssertionError: EXPANDED SEMANTIC HOLDOUT LEAKED INTO TRAINING —
    25 expanded-holdout registered domain(s) present in training

That is the guard doing its job, not a bug in the guard. The question
this script answers is whether the holdout can be made leak-free at all,
because popular domains (github.com, wikipedia.org, microsoft.com) will
appear in any large web corpus.

If they cannot be excluded by domain, the holdout is only valid for
domains that are genuinely rare.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.datasets import load_processed


def main() -> int:
    expanded = Path(__file__).resolve().parents[1] / "app" / "ml" / "semantic_cases_expanded.py"
    if not expanded.exists():
        print(f"expanded case file not present: {expanded}")
        return 1

    import importlib.util

    spec = importlib.util.spec_from_file_location("expanded_cases", expanded)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cases = getattr(module, "EXPANDED_LEGITIMATE_CASES", [])
    print(f"expanded legitimate cases: {len(cases)}")

    # Which registered domains do these holdout URLs belong to?
    from app.services.url_analyzer import InvalidURLError, normalize

    domains: Counter[str] = Counter()
    for case in cases:
        url = getattr(case, "url", None) or (case[0] if isinstance(case, tuple) else None)
        if not url:
            continue
        try:
            parsed = normalize(url)
        except InvalidURLError:
            continue
        domains[parsed.registered_domain or parsed.hostname] += 1

    print(f"distinct registered domains in holdout: {len(domains)}")
    print()

    # How many of those appear in each training corpus?
    print("=== holdout domain overlap with training corpora ===")
    for name in ("phiusil", "mud2026", "realistic"):
        try:
            rows = load_processed(name)
        except Exception:
            continue
        present = Counter()
        for row in rows:
            present[row.registered_domain] += 1
        shared = [d for d in domains if d in present]
        print(
            f"  {name:12} shared={len(shared):3}/{len(domains):<4} "
            f"({len(shared) / max(len(domains), 1):5.1%})"
        )

    print()
    print("=== the shared domains ===")
    all_present: Counter[str] = Counter()
    for name in ("phiusil", "mud2026", "realistic"):
        try:
            rows = load_processed(name)
        except Exception:
            continue
        present = {r.registered_domain for r in rows}
        for d in domains:
            if d in present:
                all_present[d] += 1

    for domain, hits in all_present.most_common():
        print(f"  {domain:32} present in {hits} corpora, "
              f"{domains[domain]} holdout case(s)")

    print()
    print("CONSEQUENCE")
    print("  Popular domains (github.com, wikipedia.org, microsoft.com) cannot")
    print("  be held out by domain - they occur in every web corpus. Excluding")
    print("  them by domain would remove the most valuable cases.")
    print()
    print("  Two defensible options:")
    print("   1. Hold out by EXACT URL. Legitimate, but a near-duplicate path")
    print("      on the same domain would still be memorised, so the measured")
    print("      false-positive rate stays optimistic.")
    print("   2. Hold out by domain and ACCEPT that popular domains cannot be")
    print("      tested, reporting the holdout as covering rare/typical domains")
    print("      only.")
    print()
    print("  Either is defensible. What is NOT defensible is reporting holdout")
    print("  scores from a set whose domains appear in training, which is what")
    print("  the guard correctly refused to do.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())