"""
Split strategies, with leakage control.

Phase 2B requires two evaluation designs, because they answer different
questions:

  RANDOM  — the conventional academic setup. Answers "how well does this
            model separate these two populations of URLs?"

  GROUPED — splits by REGISTERED DOMAIN, so every URL from one domain
            lands in exactly one partition. Answers the harder and more
            useful question: "does this model work on domains it has
            never seen?"

The grouped split is the one that matters for a deployed system. A model
that scores 99% randomly but 88% grouped has partly memorised domains,
not learned phishing structure. Both numbers are reported; neither is
hidden.

Grouping key note: `login.example.com`, `verify.example.com` and
`example.com/reset` all share the registered domain `example.com` and
therefore stay together. This is the entire point of the grouped split.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

from app.ml.datasets import AuditedRow

RANDOM_STATE = 42


class DomainLeakageError(AssertionError):
    """Raised when a domain appears in more than one partition.

    This is a hard experiment failure, not a warning. A leaked domain
    invalidates every metric computed on that split, so the run must stop
    rather than report numbers that look fine and mean nothing.
    """


@dataclass
class SplitBundle:
    """One train/validation/test partition of the dataset."""

    strategy: str
    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray

    train_domains: set[str] = field(default_factory=set)
    val_domains: set[str] = field(default_factory=set)
    test_domains: set[str] = field(default_factory=set)

    def assert_no_domain_leakage(self) -> None:
        """Fail loudly if any domain spans two partitions."""
        overlaps = {
            "train/val": self.train_domains & self.val_domains,
            "train/test": self.train_domains & self.test_domains,
            "val/test": self.val_domains & self.test_domains,
        }
        violations = {k: v for k, v in overlaps.items() if v}
        if violations:
            detail = "; ".join(
                f"{pair}: {len(v)} shared domains (e.g. {sorted(v)[:5]})"
                for pair, v in violations.items()
            )
            raise DomainLeakageError(
                f"Registered-domain leakage detected in the "
                f"{self.strategy} split — {detail}. Metrics from this split "
                f"would be invalid."
            )

    def summary(self, y: np.ndarray) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "train_rows": int(len(self.train_idx)),
            "val_rows": int(len(self.val_idx)),
            "test_rows": int(len(self.test_idx)),
            "train_phishing_rate": round(float(y[self.train_idx].mean()), 4),
            "val_phishing_rate": round(float(y[self.val_idx].mean()), 4),
            "test_phishing_rate": round(float(y[self.test_idx].mean()), 4),
            "train_domains": len(self.train_domains),
            "val_domains": len(self.val_domains),
            "test_domains": len(self.test_domains),
            "domain_overlap_train_test": len(
                self.train_domains & self.test_domains
            ),
            "domain_overlap_train_val": len(self.train_domains & self.val_domains),
        }


def grouped_split(
    rows: list[AuditedRow],
    y: np.ndarray,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = RANDOM_STATE,
) -> SplitBundle:
    """Train/val/test split where a registered domain never spans splits.

    Uses StratifiedGroupKFold twice:
      1. carve off the test fold, keeping whole domains together
      2. carve validation out of what remains, again by domain

    Stratification is approximate by nature here — a domain holding only
    one class cannot be split proportionally — so the achieved class
    balance is measured and reported rather than assumed.
    """
    groups = np.array([row.registered_domain for row in rows])

    # --- test fold ---
    outer = StratifiedGroupKFold(
        n_splits=int(round(1 / test_size)), shuffle=True, random_state=random_state
    )
    trainval_idx, test_idx = next(outer.split(np.zeros(len(y)), y, groups))

    # --- validation fold, from the remaining data ---
    val_fraction = val_size / (1.0 - test_size)
    inner = StratifiedGroupKFold(
        n_splits=int(round(1 / val_fraction)),
        shuffle=True,
        random_state=random_state,
    )
    y_inner = y[trainval_idx]
    groups_inner = groups[trainval_idx]
    rel_train, rel_val = next(inner.split(np.zeros(len(y_inner)), y_inner, groups_inner))

    train_idx = trainval_idx[rel_train]
    val_idx = trainval_idx[rel_val]

    bundle = SplitBundle(
        strategy="grouped_domain",
        train_idx=train_idx,
        val_idx=val_idx,
        test_idx=test_idx,
        train_domains=set(groups[train_idx]),
        val_domains=set(groups[val_idx]),
        test_domains=set(groups[test_idx]),
    )
    # Hard gate: refuse to hand back a leaky split.
    bundle.assert_no_domain_leakage()
    return bundle


def random_split(
    y: np.ndarray,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = RANDOM_STATE,
) -> SplitBundle:
    """Conventional stratified random split.

    Domains are EXPECTED to span partitions here — that is precisely the
    source of optimism that the grouped split exists to quantify. No
    domain-leakage assertion is applied, by design.
    """
    trainval_idx, test_idx = train_test_split(
        np.arange(len(y)),
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    val_fraction = val_size / (1.0 - test_size)
    train_idx, val_idx = train_test_split(
        trainval_idx,
        test_size=val_fraction,
        random_state=random_state,
        stratify=y[trainval_idx],
    )
    return SplitBundle(
        strategy="random",
        train_idx=train_idx,
        val_idx=val_idx,
        test_idx=test_idx,
    )


def cross_val_folds(
    y: np.ndarray,
    groups: np.ndarray | None,
    n_splits: int = 5,
    random_state: int = RANDOM_STATE,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Cross-validation folds, grouped when groups are supplied."""
    if groups is None:
        from sklearn.model_selection import StratifiedKFold

        splitter = StratifiedKFold(
            n_splits=n_splits, shuffle=True, random_state=random_state
        )
        return list(splitter.split(np.zeros(len(y)), y))
    splitter = StratifiedGroupKFold(
        n_splits=n_splits, shuffle=True, random_state=random_state
    )
    return list(splitter.split(np.zeros(len(y)), y, groups))
