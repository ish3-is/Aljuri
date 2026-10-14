"""
Multi-corpus dataset construction.

The requirement is not "concatenate the corpora". MUD is 513k rows and
PhiUSIIL is 235k, and their class ratios differ sharply:

    PhiUSIIL   134,850 legitimate / 100,512 phishing  (57/43)
    MUD 2026   421,974 benign     /  91,600 phishing  (82/18)

A naive concatenation would let MUD's benign class dominate, and the
model would learn MUD's notion of benign rather than phishing generally.
So sampling is stratified across BOTH class and corpus, targeting a
balanced four-way distribution:

    PhiUSIIL legitimate | PhiUSIIL phishing
    MUD benign          | MUD phishing

The target count per cell is the smallest cell size, capped for
tractability. Every source therefore materially contributes, and no
source's majority class swamps the rest.

Domain overlap between corpora is measured rather than assumed, and
cross-corpus duplicate URLs are removed before sampling — otherwise the
same URL could appear in both training and test under different
sources.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from app.ml.datasets import LEGITIMATE, PHISHING, AuditedRow

# Cap on total rows, for tractability. 400k featurizes in ~35s at the
# ~11.8k rows/s this pipeline sustains.
MAX_TOTAL_ROWS = 400_000
MIN_PER_CELL = 20_000


@dataclass
class Cell:
    """One (corpus, class) stratum."""

    corpus: str
    label: int
    rows: list[AuditedRow] = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"{self.corpus}|{'phishing' if self.label == PHISHING else 'legitimate'}"


@dataclass
class MultiCorpusDataset:
    rows: list[AuditedRow]
    cell_counts: dict[str, int]
    overlap: dict[str, object]
    sampling: dict[str, object]

    def label_array(self) -> np.ndarray:
        return np.asarray([r.label for r in self.rows], dtype=int)

    def groups(self) -> np.ndarray:
        """Registered domain per row — the grouped-split key."""
        return np.asarray([r.registered_domain for r in self.rows])

    def corpus_array(self) -> np.ndarray:
        return np.asarray([r.source for r in self.rows])

    def summary(self) -> dict[str, object]:
        labels = self.label_array()
        corpora = self.corpus_array()
        counts = Counter(
            f"{c}|{'phishing' if l == PHISHING else 'legitimate'}"
            for c, l in zip(corpora, labels)
        )
        return {
            "total_rows": len(self.rows),
            "cell_counts": counts,
            "phishing_rate": float(labels.mean()),
            "corpus_distribution": dict(Counter(corpora)),
            "overlap": self.overlap,
            "sampling": self.sampling,
        }


def measure_overlap(
    per_corpus: dict[str, Sequence[AuditedRow]],
) -> dict[str, object]:
    """Measure URL/domain overlap between corpora.

    Overlap matters twice:
      1. a URL present in both corpora must not straddle train/test
      2. a high overlap means the corpora are less independent than
         they appear, which weakens any generalization claim
    """
    names = sorted(per_corpus)
    if len(names) < 2:
        return {"pairs": [], "note": "fewer than two corpora"}

    pairs: list[dict[str, object]] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            urls_a = {r.normalized.lower() for r in per_corpus[a]}
            urls_b = {r.normalized.lower() for r in per_corpus[b]}
            dom_a = {r.registered_domain for r in per_corpus[a]}
            dom_b = {r.registered_domain for r in per_corpus[b]}
            host_a = {r.hostname for r in per_corpus[a]}
            host_b = {r.hostname for r in per_corpus[b]}
            pairs.append(
                {
                    "pair": f"{a} vs {b}",
                    "same_normalized_url": len(urls_a & urls_b),
                    "same_registered_domain": len(dom_a & dom_b),
                    "same_hostname": len(host_a & host_b),
                    "url_jaccard": round(
                        len(urls_a & urls_b) / max(len(urls_a | urls_b), 1), 6
                    ),
                    "domain_jaccard": round(
                        len(dom_a & dom_b) / max(len(dom_a | dom_b), 1), 6
                    ),
                    "domain_overlap_rate_against_a": round(
                        len(dom_a & dom_b) / max(len(dom_a), 1), 6
                    ),
                    "domain_overlap_rate_against_b": round(
                        len(dom_a & dom_b) / max(len(dom_b), 1), 6
                    ),
                }
            )
    return {"pairs": pairs}


def build(
    per_corpus: dict[str, Sequence[AuditedRow]],
    *,
    max_total: int = MAX_TOTAL_ROWS,
    min_per_cell: int = MIN_PER_CELL,
    seed: int = 42,
) -> MultiCorpusDataset:
    """Build a balanced multi-corpus training set.

    Cross-corpus duplicate URLs are dropped before sampling: a URL in
    both corpora is one observation, not two, and keeping both would let
    an identical string appear on both sides of a split.
    """
    rng = np.random.default_rng(seed)

    overlap = measure_overlap(per_corpus)

    # --- drop cross-corpus duplicate URLs, keeping the first corpus ---
    seen: set[str] = set()
    deduplicated: dict[str, list[AuditedRow]] = {}
    dropped_for_overlap = 0
    for corpus in sorted(per_corpus):
        kept: list[AuditedRow] = []
        for row in per_corpus[corpus]:
            key = row.normalized.lower()
            if key in seen:
                dropped_for_overlap += 1
                continue
            seen.add(key)
            kept.append(row)
        deduplicated[corpus] = kept

    # --- strata ---
    cells: list[Cell] = []
    for corpus in sorted(deduplicated):
        for label in (LEGITIMATE, PHISHING):
            subset = [r for r in deduplicated[corpus] if r.label == label]
            if subset:
                cells.append(Cell(corpus=corpus, label=label, rows=subset))

    if not cells:
        raise ValueError("no rows available to build a multi-corpus dataset")

    # --- target per cell ---
    smallest = min(len(c.rows) for c in cells)
    target = max(min(smallest, max_total // len(cells)), min_per_cell)
    target = min(target, smallest)

    sampled: list[AuditedRow] = []
    cell_counts: dict[str, int] = {}
    for cell in cells:
        if len(cell.rows) <= target:
            chosen = cell.rows
        else:
            indices = rng.choice(len(cell.rows), size=target, replace=False)
            chosen = [cell.rows[int(i)] for i in indices]
        sampled.extend(chosen)
        cell_counts[cell.name] = len(chosen)

    # Deterministic order: stable regardless of dict iteration order.
    sampled.sort(key=lambda r: (r.source, r.normalized))

    return MultiCorpusDataset(
        rows=sampled,
        cell_counts=cell_counts,
        overlap={
            **overlap,
            "cross_corpus_duplicate_urls_dropped": dropped_for_overlap,
        },
        sampling={
            "target_per_cell": target,
            "cells": [c.name for c in cells],
            "max_total": max_total,
            "seed": seed,
            "strategy": (
                "stratified by (corpus, class); target is the smallest "
                "cell size, capped by max_total/len(cells)"
            ),
        },
    )