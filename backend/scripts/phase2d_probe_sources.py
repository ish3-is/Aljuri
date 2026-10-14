"""
Audit the Phase 2D candidate sources before anything is trained on them.

Phishtank and Tranco are downloaded. The question this script answers is
whether they actually contain the structure Phase 2D needs, measured
rather than assumed:

  * PhishTank is expected to be phishing with real paths.
  * Tranco is known to be bare domains only, which makes it useful for
    DOMAIN DIVERSITY but useless for path realism.

Everything here is measured. Nothing is taken on faith from a README.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

csv.field_size_limit(10**9)

BACKEND = Path(__file__).resolve().parents[1]
RAW = BACKEND / "datasets" / "raw" / "phase2d"
RESULTS = BACKEND / "results" / "phase2d"


def structure_stats(urls: list[str], label: str, sample: int = 20000) -> dict[str, object]:
    """Measure the structural profile of a URL list."""
    step = max(len(urls) // sample, 1)
    taken = urls[::step][:sample]

    with_path = query = fragment = https = 0
    depths: list[int] = []
    lengths: list[int] = []
    hosts: Counter[str] = Counter()
    domains: Counter[str] = Counter()

    for raw in taken:
        try:
            parts = urlsplit(raw.strip())
        except ValueError:
            continue
        host = parts.hostname or ""
        path = parts.path or ""
        if host:
            hosts[host] += 1
            domains[".".join(host.split(".")[-2:])] += 1
        if path.strip("/"):
            with_path += 1
            depths.append(len([s for s in path.split("/") if s]))
        if parts.query:
            query += 1
        if parts.fragment:
            fragment += 1
        if parts.scheme == "https":
            https += 1
        lengths.append(len(raw))

    n = max(len(taken), 1)
    return {
        "source": label,
        "n_sampled": len(taken),
        "pct_with_path": round(with_path / n * 100, 2),
        "pct_with_query": round(query / n * 100, 2),
        "pct_with_fragment": round(fragment / n * 100, 2),
        "pct_https": round(https / n * 100, 2),
        "median_path_depth": sorted(depths)[len(depths) // 2] if depths else 0,
        "max_path_depth": max(depths) if depths else 0,
        "median_url_length": sorted(lengths)[len(lengths) // 2] if lengths else 0,
        "distinct_hosts_sampled": len(hosts),
        "distinct_registered_domains_sampled": len(domains),
        "domain_diversity_ratio": round(len(domains) / n, 4),
    }


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    # --- PhishTank ---
    pt = RAW / "phishtank_online_valid.csv"
    if pt.exists():
        urls: list[str] = []
        with pt.open("r", encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                url = (record.get("url") or "").strip()
                if url:
                    urls.append(url)
        rows.append(structure_stats(urls, "phishtank_online_valid"))
        print(f"PhishTank: {len(urls):,} URLs")
        for url in urls[:3]:
            print(f"   e.g. {url[:78]}")

    # --- Tranco ---
    tz = RAW / "tranco_top1m.csv.zip"
    if tz.exists():
        domains: list[str] = []
        with zipfile.ZipFile(tz) as z:
            with z.open("top-1m.csv") as handle:
                for line in handle:
                    parts = line.decode("utf-8", errors="replace").strip().split(",")
                    if len(parts) >= 2:
                        domains.append(parts[1])
        # Tranco is rank,domain — reconstruct as bare URLs to measure.
        tranco_urls = [f"https://{d}/" for d in domains]
        rows.append(structure_stats(tranco_urls, "tranco_top1m"))
        print(f"\nTranco: {len(domains):,} domains")
        for url in tranco_urls[:3]:
            print(f"   e.g. {url}")

    out = RESULTS / "source_structure_probe.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'source':28}{'%path':>8}{'%query':>8}{'medDepth':>10}{'domains':>10}")
    for row in rows:
        print(
            f"{row['source']:28}{row['pct_with_path']:8.2f}"
            f"{row['pct_with_query']:8.2f}{row['median_path_depth']:10}"
            f"{row['distinct_registered_domains_sampled']:10,}"
        )
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())