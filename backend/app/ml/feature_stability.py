"""
Feature stability analysis.

The central question of Phase 2C: which of BASIRAH's 39 features mean the
same thing in every corpus?

Phase 2B found that 20 of 39 had OPPOSITE class associations between
PhiUSIIL and MUD, which is why a PhiUSIIL-trained model scored ROC-AUC
0.271 (below chance) on MUD. This module turns that from a manual
observation into a repeatable classification, so feature selection can
be evidence-based rather than guesswork.

Classification, by agreement between corpora:

    STABLE      same direction AND similar magnitude
    WEAK        same direction, small effect in at least one corpus
    CORPUS-SENSITIVE  same direction, but magnitude varies a lot
    INVERTED    opposite direction — the dangerous category

INVERTED features are not automatically removed. A feature can be
inverted because of a corpus artifact OR because the two corpora
genuinely contain different phishing styles. Phase 2C evaluates the
trade-off empirically via the variant comparison rather than deciding
by assertion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

import numpy as np

from app.ml.datasets import LEGITIMATE, PHISHING


class Stability(str, Enum):
    STABLE = "STABLE"
    WEAK = "WEAK"
    CORPUS_SENSITIVE = "CORPUS_SENSITIVE"
    INVERTED = "INVERTED"


@dataclass
class FeatureStability:
    """One feature's behaviour across every corpus supplied."""

    name: str
    per_corpus: dict[str, dict[str, float]] = field(default_factory=dict)
    classification: Stability = Stability.WEAK
    notes: str = ""

    @property
    def n_inverted(self) -> int:
        return int(sum(1 for c in self.per_corpus.values() if c.get("direction", 0) < 0))

    def to_row(self) -> dict[str, object]:
        row: dict[str, object] = {
            "feature": self.name,
            "classification": self.classification.value,
            "corpora": len(self.per_corpus),
            "notes": self.notes,
        }
        for corpus, stats in self.per_corpus.items():
            row[f"{corpus}_mean_phishing"] = round(stats.get("mean_phishing", 0.0), 5)
            row[f"{corpus}_mean_legitimate"] = round(stats.get("mean_legitimate", 0.0), 5)
            row[f"{corpus}_effect"] = round(stats.get("effect", 0.0), 5)
            row[f"{corpus}_direction"] = int(stats.get("direction", 0))
            row[f"{corpus}_separation"] = round(stats.get("separation", 0.0), 5)
        row["n_inverted_corpus"] = self.n_inverted
        row["max_abs_effect"] = round(
            max((abs(s.get("effect", 0.0)) for s in self.per_corpus.values()), default=0.0), 5
        )
        return row

    def names(self) -> list[str]:
        return list(self.per_corpus)


# Thresholds, stated so the classification is auditable.
MIN_EFFECT = 0.01
"""Below this, the feature barely separates its own corpus."""

NOISE_FLOOR = 0.10
"""A feature whose largest absolute class effect is under this in every
corpus is treated as noise rather than inverted. Pure noise produces
opposing signs by chance; without this floor a meaningless column gets
classified INVERTED and the inversion count becomes meaningless."""

MIN_MEAN_ABS_EFFECT = 0.05
"""A corpus where a feature is this weak makes it CORPUS-SENSITIVE."""

EFFECT_VARIATION_RATIO = 3.0
"""Max/min absolute effect above this means the feature's strength
varies substantially between corpora."""


def analyse(
    feature_names: Sequence[str],
    matrices: dict[str, np.ndarray],
    labels: dict[str, np.ndarray],
) -> list[FeatureStability]:
    """Classify every feature using per-corpus class means.

    `matrices[corpus]` must be the FULL extractor output, aligned with
    `feature_names`, so direction comparisons are meaningful.
    """
    results: list[FeatureStability] = []

    for index, name in enumerate(feature_names):
        entry = FeatureStability(name=name)
        effects: list[float] = []
        directions: list[int] = []

        for corpus, X in matrices.items():
            y = labels[corpus]
            phishing = X[y == PHISHING, index]
            legitimate = X[y == LEGITIMATE, index]

            mean_p = float(phishing.mean()) if len(phishing) else 0.0
            mean_l = float(legitimate.mean()) if len(legitimate) else 0.0
            effect = mean_p - mean_l
            direction = 0 if abs(effect) < MIN_EFFECT else (1 if effect > 0 else -1)

            # Standardised separation: how well the feature separates
            # its own classes, independent of its units.
            pooled = np.sqrt(
                (float(phishing.var()) if len(phishing) > 1 else 0.0)
                + (float(legitimate.var()) if len(legitimate) > 1 else 0.0)
            ) / 2.0
            separation = effect / pooled if pooled > 1e-12 else 0.0

            entry.per_corpus[corpus] = {
                "mean_phishing": mean_p,
                "mean_legitimate": mean_l,
                "effect": effect,
                "direction": direction,
                "separation": separation,
                "n_phishing": int(len(phishing)),
                "n_legitimate": int(len(legitimate)),
            }
            effects.append(effect)
            directions.append(direction)

        nonzero = [d for d in directions if d != 0]
        opposite = len({d for d in nonzero if d < 0}) > 0 and len(
            {d for d in nonzero if d > 0}
        ) > 0

        abs_effects = [abs(e) for e in effects]
        max_effect = max(abs_effects, default=0.0)
        min_effect = min(abs_effects, default=0.0)

        # A feature must clear NOISE_FLOOR in at least one corpus before
        # its direction is meaningful. Pure noise produces opposing signs
        # by chance, and treating that as an inversion would inflate the
        # INVERTED count with meaningless columns — the opposite failure
        # to missing a real one.
        is_noise = max_effect < NOISE_FLOOR

        if is_noise:
            entry.classification = Stability.WEAK
            entry.notes = "no effect above the noise floor in any corpus"
        elif opposite:
            entry.classification = Stability.INVERTED
            entry.notes = "opposite class association between corpora"
        elif max_effect < MIN_MEAN_ABS_EFFECT:
            entry.classification = Stability.WEAK
            entry.notes = "negligible effect in every corpus"
        elif min_effect < min(MIN_EFFECT * 5, max_effect * 0.05):
            entry.classification = Stability.CORPUS_SENSITIVE
            entry.notes = "strong in one corpus, near-absent in another"
        elif min_effect > 0 and max_effect / min_effect > EFFECT_VARIATION_RATIO:
            entry.classification = Stability.CORPUS_SENSITIVE
            entry.notes = (
                f"effect magnitude varies {max_effect / min_effect:.1f}x across corpora"
            )
        else:
            entry.classification = Stability.STABLE

        results.append(entry)

    return results


def indices_for(
    feature_names: Sequence[str],
    results: Sequence[FeatureStability],
    categories: set[Stability],
) -> list[int]:
    """Column indices of features in the given stability categories."""
    by_name = {r.name: r for r in results}
    return [
        i
        for i, name in enumerate(feature_names)
        if name in by_name and by_name[name].classification in categories
    ]


def counts_by_class(results: Sequence[FeatureStability]) -> dict[str, int]:
    counts: dict[str, int] = {c.value: 0 for c in Stability}
    for result in results:
        counts[result.classification.value] += 1
    return counts