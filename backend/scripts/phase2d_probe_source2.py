"""Evaluate a second candidate legitimate corpus before adopting it.

The first source (HF ealvaradob) is already in use. A second
independently-licensed source would improve domain diversity, but only
if its rows are actually legitimate-looking.

Sampled URLs from it include `ftp://ftp.cs.utexas.edu/pub/garbage/` and
`https://0064bdb.netsolhost.com/` — a parking/hosting domain. Those are
warnings, not proof, so this measures rather than assumes.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

csv.field_size_limit(10**9)

SOURCE = Path("C:/Users/hp/basirah_data/majestic_legit_urls.txt")

# Hosting/parking providers that appear in bulk in scraped corpora.
PARKING_MARKERS = (
    "netsolhost", "parklogic", "sedoparking", "above.com", "hugedomains",
    "domainmarket", "dan.com", "afternic", "dan.com", "undeveloped",
    "cashparking", "parkingcrew", "brandbucket", "godaddy.com/forsale",
)

# Obvious placeholder / junk markers.
JUNK_MARKERS = ("garbage", "test123", "example.invalid", "/pub/", "lorem")


def main() -> int:
    if not SOURCE.exists():
        print(f"missing {SOURCE}")
        return 1

    lines = SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
    urls = [line.strip() for line in lines if line.strip()]
    n = len(urls)

    schemes: Counter[str] = Counter()
    with_path = with_query = 0
    parking = junk = 0
    hosts: Counter[str] = Counter()
    depths: list[int] = []
    bad_scheme = 0

    for raw in urls:
        try:
            parts = urlsplit(raw)
        except ValueError:
            continue
        host = (parts.hostname or "").lower()
        schemes[parts.scheme or "<none>"] += 1
        if parts.scheme not in ("http", "https"):
            bad_scheme += 1
        path = (parts.path or "").strip("/")
        if path:
            with_path += 1
            depths.append(len([p for p in path.split("/") if p]))
        if parts.query:
            with_query += 1
        if host:
            hosts[host] += 1
        low = raw.lower()
        if any(marker in low for marker in PARKING_MARKERS):
            parking += 1
        if any(marker in low for marker in JUNK_MARKERS):
            junk += 1

    print(f"source : {SOURCE}")
    print(f"rows   : {n:,}")
    print()
    print("scheme distribution:")
    for scheme, count in schemes.most_common(8):
        print(f"   {scheme:12} {count:9,}  ({count / n * 100:5.2f}%)")
    print()
    print(f"  non-http(s) schemes : {bad_scheme:9,}  ({bad_scheme / n * 100:5.2f}%)")
    print(f"  with a path         : {with_path:9,}  ({with_path / n * 100:5.2f}%)")
    print(f"  with a query        : {with_query:9,}  ({with_query / n * 100:5.2f}%)")
    print(f"  median path depth   : {sorted(depths)[len(depths)//2] if depths else 0}")
    print(f"  parking-provider hits: {parking:8,}  ({parking / n * 100:5.2f}%)")
    print(f"  junk-marker hits    : {junk:8,}  ({junk / n * 100:5.2f}%)")
    print(f"  distinct hosts      : {len(hosts):,}")
    print()
    print("most repeated hosts:")
    for host, count in hosts.most_common(8):
        print(f"   {count:7,}  {host}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())