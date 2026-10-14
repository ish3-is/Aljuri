"""
Phase 2E source audit — the Mendeley legitimate corpus.

Phase 2D staged this file but did not adopt it. Staging is not evidence
of safety, so everything the brief requires is measured here:

  1. exact source file        6. path prevalence
  2. provenance               7. HTTPS prevalence
  3. licence                  8. query prevalence
  4. SHA256                   9. host concentration
  5. label semantics         10. domain diversity
                              11. overlap with all four existing corpora

The concentration measurement drives the per-domain cap, so it is
reported at the top-1/10/100 levels rather than as a single ratio.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

csv.field_size_limit(10**9)

BACKEND = Path(__file__).resolve().parents[1]
SOURCE = BACKEND / "datasets" / "raw" / "phase2d" / "mendeley_legit_urls.txt"
RESULTS = BACKEND / "results" / "phase2e"

SOURCE_META = {
    "name": "Mendeley Data 'Phishing URL dataset' (legitimate subset)",
    "source_url": (
        "https://data.mendeley.com/public-files/datasets/vfszbj9b36/files/"
        "f0de314f-ea72-4385-9faa-f06593bb0a2d/file_downloaded"
    ),
    "license": "CC BY 4.0",
    "label_semantics": {
        "all_rows": "legitimate",
        "documented": True,
        "evidence": "upstream corpus labels these benign",
    },
    "assumption": (
        "UPSTREAM-CURATED BENIGN CANDIDATE CORPUS. Labels are taken from "
        "the upstream corpus and are NOT independently verified. No URL "
        "was visited. This is weaker provenance than PhishTank, whose "
        "labels are human-verified."
    ),
}


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    lines = SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
    urls = [l.strip() for l in lines if l.strip()]

    n = len(urls)
    with_path = with_query = https = malformed = 0
    depths: list[int] = []
    hosts: Counter[str] = Counter()
    reg_domains: Counter[str] = Counter()

    for raw in urls:
        try:
            parts = urlsplit(raw)
        except ValueError:
            malformed += 1
            continue
        host = (parts.hostname or "").lower()
        if not host:
            malformed += 1
            continue
        hosts[host] += 1
        reg_domains[".".join(host.split(".")[-2:])] += 1
        path = (parts.path or "").strip("/")
        if path:
            with_path += 1
            depths.append(len([p for p in path.split("/") if p]))
        if parts.query:
            with_query += 1
        if parts.scheme == "https":
            https += 1

    valid = max(n - malformed, 1)
    top = reg_domains.most_common(100)
    total = sum(reg_domains.values())

    audit = {
        **SOURCE_META,
        "file": str(SOURCE.relative_to(BACKEND.parent)).replace("\\", "/"),
        "sha256": digest,
        "size_bytes": SOURCE.stat().st_size,
        "raw_rows": n,
        "usable_rows": n - malformed,
        "malformed": malformed,
        "pct_with_path": round(with_path / valid * 100, 3),
        "pct_with_query": round(with_query / valid * 100, 3),
        "pct_https": round(https / valid * 100, 3),
        "median_path_depth": sorted(depths)[len(depths) // 2] if depths else 0,
        "distinct_hosts": len(hosts),
        "distinct_registered_domains": len(reg_domains),
        "top_domain_share_pct": round(top[0][1] / total * 100, 3),
        "top10_domain_share_pct": round(sum(c for _, c in top[:10]) / total * 100, 3),
        "top100_domain_share_pct": round(sum(c for _, c in top[:100]) / total * 100, 3),
        "largest_domains": [{"domain": d, "urls": c} for d, c in top[:10]],
    }

    print("=== SOURCE AUDIT ===")
    for key in ("raw_rows", "usable_rows", "malformed", "pct_with_path",
                "pct_with_query", "pct_https", "median_path_depth",
                "distinct_hosts", "distinct_registered_domains",
                "top_domain_share_pct", "top10_domain_share_pct",
                "top100_domain_share_pct"):
        print(f"  {key:32} {audit[key]:,}")
    print(f"  {'sha256':32} {digest[:40]}...")
    print()
    print("  largest domains:")
    for entry in audit["largest_domains"][:6]:
        print(f"     {entry['urls']:7,}  {entry['domain']}")

    # ---- overlap with every existing corpus ----
    print()
    print("=== OVERLAP WITH EXISTING CORPORA ===")
    from app.ml.datasets import load_processed

    own = set(reg_domains)
    overlaps = {}
    for name in ("phiusil", "mud2026", "realistic", "phishtank"):
        try:
            existing = {r.registered_domain for r in load_processed(name)}
        except Exception:
            continue
        shared = own & existing
        overlaps[name] = {
            "shared_registered_domains": len(shared),
            "pct_of_this_corpus": round(len(shared) / max(len(own), 1) * 100, 2),
            "pct_of_that_corpus": round(len(shared) / max(len(existing), 1) * 100, 2),
        }
        print(f"  {name:12} shared={len(shared):7,}  "
              f"{len(shared) / max(len(own), 1) * 100:5.1f}% of this corpus")
    audit["overlap"] = overlaps

    # ---- why the cap matters ----
    print()
    print("=== CONCENTRATION DRIVES THE CAP ===")
    for cap in (25, 50, 100, 250):
        kept = sum(min(c, cap) for c in reg_domains.values())
        kept_domains = sum(1 for c in reg_domains.values() if c >= 1)
        top10_after = sum(min(c, cap) for _, c in top[:10])
        print(f"  cap={cap:4}/domain -> rows={kept:7,}  domains={kept_domains:7,}  "
              f"top10 share={top10_after / max(kept, 1) * 100:5.1f}%")

    out = RESULTS / "source_audit.json"
    out.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())