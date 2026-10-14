# Phase 2E — Methodology

> Feeds **Chapter 5 — Methodology**. Final URL-intelligence phase.

---

## 1. Objective

Can the remaining HTTPS and source-distribution problems be corrected
without sacrificing the Phase 2D gains?

**Answer: no, and the phase is more useful for having shown it.**

---

## 2. Source acquisition and validation

The Phase 2D-staged Mendeley corpus was audited before adoption, not
assumed safe.

| Metric | Value |
|---|---|
| Rows / usable | 345,738 / 345,738 (0 malformed) |
| **% HTTPS** | **99.99** |
| % with path | 85.04 |
| % with query | 13.29 |
| Registered domains | 84,682 |
| SHA-256 | `a5066468965c0af0842f7787631fb89f606ef681…` |
| Licence | CC BY 4.0 |
| Labels | upstream-curated, **not independently verified** |

### 2.1 The finding that shaped the phase

| Overlap with | Share of this corpus already present |
|---|---|
| MUD 2026 | **95.3%** |
| Realistic (2D) | **95.9%** |
| PhiUSIIL | 7.5% |
| PhishTank | 0.1% |

The source contributes **HTTPS realism, not domain diversity**. The brief's
stated premise for it did not hold, so any gain had to be measured rather
than assumed — and it was not found.

---

## 3. Corpus quality gate: C19–C22

Four configurable checks were added for a legitimate corpus:

| Check | Purpose |
|---|---|
| C19 | Top-domain concentration |
| C20 | Top-10-domain concentration |
| C21 | HTTPS realism |
| C22 | Per-domain cap enforcement |

**C22 caught a real bug.** `multi_corpus.build()` samples per cell, so
capping only the input pools left the assembled set above the cap. The
gate failed, the assembled set was re-capped, and the selected cap moved
25 → 100 **because the measurement changed**, not because the expectation
did.

---

## 4. Per-domain cap comparison

Tested at 25, 50 and 100, ranked on generalization only. Row count was
measured and deliberately excluded from the ranking.

| Cap | Rows | Grouped AUC | Worst-corpus AUC | PhishTank recall @0.05 |
|---|---|---|---|---|
| 25 | 179,417 | 0.9472 | 0.8431 | 0.6871 |
| 50 | 198,627 | 0.9479 | 0.8463 | 0.6815 |
| **100** | 218,285 | **0.9504** | **0.8483** | **0.7007** |

Cap 100 wins on all three generalization criteria while having the
*fewest* distinct training domains of the three.

---

## 5. Holdout integrity

| Assertion | Result |
|---|---|
| Original 14-URL set in training | **excluded** |
| Expanded-holdout domains in training | **excluded** |
| PhishTank domains in training | **excluded** |
| train ∩ test registered domains | **empty** |

The expanded set (36 URLs, 13 categories) is holdout-only. An early
smoke run **aborted** rather than train on 25 leaked domains; the domains
were then removed from training rather than the assertion weakened.

---

## 6. Matched-FPR evaluation

Mandatory, and the single most important methodological commitment in
this phase.

Models are compared at a **matched false-positive rate** — 0.01, 0.03,
0.05, 0.10 — never at each model's own threshold.

Own-threshold recall is confounded: v1 scores ~0.98 that way purely
because it flags two-thirds of all legitimate traffic. Ranking on it
would crown the model whose defect is the reason this project exists.
This exact mistake was made and corrected twice during Phase 2E.

---

## 7. Model and feature variants

Four families (LogisticRegression, RandomForest, HistGradientBoosting,
XGBoost) across variants {39, 39+uses_https, 39+uses_http, 39+both}.

Scheme variants are rejected for two independent reasons, recorded
separately:

1. **Empirical.** They improved worst-corpus AUC by only +0.029, and the
   new corpus is identifiable *by scheme alone* (corpus-classifier
   accuracy 0.8283 → 0.9278 when scheme columns are added).
2. **Architectural.** `production.py` slices to the 39-column list and
   `assert_schema_matches` would refuse a scheme-aware model at load.
   Changing that serving contract is a separate, deliberate act — not
   something a promotion decision may do silently.

---

## 8. Promotion policy

Three gates, all of which must pass, then a fallback ladder:

1. If the candidate passes every gate and improves on v3 with no
   regression → **PROMOTE v4**
2. If the candidate fails → promote v3 **only if** v3 beats v1 at every
   matched FPR and on both AUCs
3. Otherwise → **NO MODEL PROMOTED**, URL ML is research-grade

---

## 9. Reproducibility

`random_state = 42`. Smoke runs and full runs **share an output
directory**, which caused a full-scale artifact set to be overwritten
once; this is a known limitation of the harness, not of the results.

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.\.venv\Scripts\python.exe -m scripts.run_phase2e_experiment
```