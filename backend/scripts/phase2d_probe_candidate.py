"""Measure whether the candidate legitimate corpus solves the path problem.

The whole premise of Phase 2D is that real legitimate URLs have paths.
That must be MEASURED before training on it, not assumed because a
README says "legitimate".

Also audits provenance, because a scraped corpus carries assumptions
that need recording rather than trusting.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

csv.field_size_limit(10**9)

BACKEND = Path(__file__).resolve().parents[1]
RESULTS = BACKEND / "results" / "phase2d"
SOURCE = Path("C:/Users/hp/basirah_data/urls.json")


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    if not SOURCE.exists():
        print(f"missing {SOURCE}")
        return 1

    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    records = json.loads(SOURCE.read_text(encoding="utf-8"))

    stats = {0: Counter(), 1: Counter()}
    domains = {0: Counter(), 1: Counter()}
    depths = {0: [], 1: []}
    examples: dict[int, list[str]] = {0: [], 1: []}

    for row in records:
        label = int(row["label"])
        raw = (row.get("text") or "").strip()
        if not raw:
            continue
        if not raw.startswith(("http://", "https://")):
            raw = "http://" + raw
        try:
            parts = urlsplit(raw)
        except ValueError:
            continue
        host = parts.hostname or ""
        path = (parts.path or "").strip("/")
        s = stats[label]
        s["n"] += 1
        if path:
            s["path"] += 1
            depths[label].append(len([p for p in path.split("/") if p]))
        if parts.query:
            s["query"] += 1
        if parts.scheme == "https":
            s["https"] += 1
        if host:
            domains[label][".".join(host.split(".")[-2:])] += 1
            s["host"] += 1
        if len(examples[label]) < 3:
            examples[label].append(raw)

    print(f"sha256: {digest}")
    print(f"records: {len(records):,}\n")
    header = f"{'label':10}{'n':>10}{'%path':>8}{'%query':>8}{'%https':>8}{'medDepth':>10}{'domains':>10}"
    print(header)
    print("-" * len(header))
    rows = []
    for label, name in ((0, "legitimate"), (1, "phishing")):
        s = stats[label]
        n = max(s["n"], 1)
        med = sorted(depths[label])[len(depths[label]) // 2] if depths[label] else 0
        rows.append(
            {
                "label": name,
                "n": s["n"],
                "pct_with_path": round(s["path"] / n * 100, 2),
                "pct_with_query": round(s["query"] / n * 100, 2),
                "pct_https": round(s["https"] / n * 100, 2),
                "median_path_depth": med,
                "distinct_registered_domains": len(domains[label]),
            }
        )
        print(
            f"{name:10}{s['n']:>10,}{s['path'] / n * 100:8.2f}"
            f"{s['query'] / n * 100:8.2f}{s['https'] / n * 100:8.2f}"
            f"{med:>10}{len(domains[label]):>10,}"
        )

    print()
    for label in (0, 1):
        print(f"{rows[label]['label']} examples:")
        for url in examples[label]:
            print(f"   {url[:76]}")

    out = RESULTS / "candidate_corpus_structure.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwritten: {out}")

    # The headline comparison, stated explicitly.
    legit_path = rows[0]["pct_with_path"]
    phishtank_path = 60.51
    phiusil_legit_path = 0.0
    print()
    print("PATH-PRESENCE COMPARISON")
    print(f"  PhiUSIIL legitimate : {phiusil_legit_path:6.2f}%   <- the defect")
    print(f"  PhishTank phishing  : {phishtank_path:6.2f}%")
    print(f"  candidate legitimate: {legit_path:6.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())