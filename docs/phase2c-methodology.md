# Phase 2C — Methodology

> Feeds **Chapter 5 — Methodology** and the implementation sections of
> **Chapter 6**.
>
> All figures are produced by
> `backend/scripts/run_phase2c_experiment.py` and written to
> `backend/results/phase2c/`.

---

## 1. Research question

> **How does multi-corpus training affect the generalization and
> false-positive behaviour of phishing URL classifiers under dataset
> distribution shift?**

This is not a rhetorical framing. Phase 2B produced a model with
excellent in-domain metrics (grouped ROC-AUC 0.9983) that scored
**ROC-AUC 0.271** on an independent corpus — below chance — and flagged
**9 of 13** well-known legitimate URLs as phishing. Phase 2C exists to
answer whether multi-corpus training fixes that, and by how much.

### 1.1 Hypotheses

| # | Hypothesis | Test |
|---|---|---|
| H1 | Single-corpus training does not transfer | Leave-one-corpus-out |
| H2 | Corpus defects (path presence) drive false positives | Semantic regression |
| H3 | Most features are corpus-specific, not phishing-specific | Stability analysis |
| H4 | Restricting to stable features improves worst-corpus performance | Variant comparison |
| H5 | The corpora are distinguishable from features alone | Corpus-source classifier |

---

## 2. Why a corpus quality gate is mandatory

Phase 2B's three defects were invisible to every accuracy metric. The
gate (`app/ml/corpus_quality.py`) runs ten structural checks before
training and aborts on critical failure.

### 2.1 The checks

| ID | Check | Severity | What it prevents |
|---|---|---|---|
| C01 | Labels binary and canonical | critical | Silent encoding drift |
| C02 | Label orientation explicitly declared | critical | **The inverted-label defect** |
| C03 | No missing URLs | critical | Silent row loss |
| C04 | Duplicate rate ≤ 5% | critical | Inflated metrics |
| C05 | Conflicting labels ≈ 0 | critical | Labels that are not ground truth |
| C06 | **Path presence is not a class proxy** | critical | **The 9/13 false-positive defect** |
| C07 | HTTPS is not a class proxy | warning | Scheme shortcut |
| C08 | Domain repetition measured | warning | Leakage risk |
| C10 | Both classes ≥ 1% | warning | Degenerate priors |
| C11 | Malformed rate ≤ 2% | critical | Silent row loss |

### 2.2 The C06 threshold, and why it was 0.15

The first implementation used a threshold of 0.98 — the difference must
be near-perfect separation. **It passed PhiUSIIL.** The measured gap is
0.597, and the corpus is still severely degenerate.

The threshold was corrected to **0.15** after measuring. This is
recorded because it is instructive: a quality gate that is too lax is
worse than none, because it manufactures false confidence. The gate's
own docstring now carries the measurement.

---

## 3. Corpus adapters

`app/ml/corpus_adapters.py`. Each adapter declares, in words, what its
label column means. Numeric orientation is never inferred.

| Corpus | Class names | Orientation | Source of truth |
|---|---|---|---|
| PhiUSIIL | numeric | **−1** (1 = legitimate) | UCI id 967 documentation |
| MUD 2026 | `benign` / `defacement` / `phishing` / `malware` | +1 (textual) | Dataset schema |

`detect_label_orientation()` returns `0` for a bare numeric column, and
`LabelOrientationError` aborts. That refusal is what Phase 2B lacked.

### 3.1 MUD class exclusion

Only `benign` and `phishing` are loaded. `defacement` (95,285) and
`malware` (23,577) are excluded because they are different threat
models; the exclusion is counted and reported, never silent.

---

## 4. Multi-corpus construction

Naive concatenation would let MUD's benign class dominate. Sampling is
stratified across **(corpus × class)**:

```
PhiUSIIL legitimate | PhiUSIIL phishing
MUD benign          | MUD phishing
```

Target per cell = smallest cell size, capped at `max_total / 4` for
tractability. Cross-corpus duplicate URLs are removed *before*
sampling, since one URL appearing in two corpora is one observation, not
two.

---

## 5. Feature stability

`app/ml/feature_stability.py`. For every feature, per corpus:
mean on phishing, mean on legitimate, effect, and direction.

| Classification | Meaning |
|---|---|
| STABLE | same direction, comparable magnitude |
| CORPUS-SENSITIVE | same direction, magnitude varies sharply |
| WEAK | below the noise floor, or negligible everywhere |
| INVERTED | **opposite direction between corpora** |

**A noise floor of 0.10 is applied before direction is considered.**
Without it, pure noise produces opposing signs by chance and inflates
the INVERTED count with meaningless columns. This was caught by a unit
test that asserts a noise column is never classified INVERTED — a test
that matters because 15 of 39 real features were classified as such.

---

## 6. Evaluation design

Four targets, all grouped by registered domain:

| Target | Purpose |
|---|---|
| Mixed grouped holdout | Overall performance |
| PhiUSIIL holdout | In-domain behaviour |
| MUD holdout | Transfer behaviour |

Leave-one-corpus-out adds:

| Experiment | Trains on | Tests on |
|---|---|---|
| A | PhiUSIIL | MUD |
| B | MUD | PhiUSIIL |
| C | both | mixed grouped holdout |
| D | both | PhiUSIIL holdout |
| E | both | MUD holdout |

For A and B the held-out corpus's **domains are removed from training
entirely**, not merely held out, so no shared domain can leak.

Leakage is asserted, not assumed:
`train_domains ∩ test_domains == ∅` aborts the run.

---

## 7. Feature variants

Four subsets, so feature selection is evidence-based rather than assumed:

| Variant | Features |
|---|---|
| A `all_features` | all 39 |
| B `stable_only` | STABLE only |
| C `stable_plus_weak` | STABLE + WEAK |
| D `exclude_inverted` | everything except INVERTED |

**Inverted features are not automatically removed.** A feature can be
inverted because of a corpus artifact *or* because the corpora contain
genuinely different phishing styles. The variant comparison decides
empirically.

---

## 8. Model selection policy

Ranked on, in order:

1. **worst-corpus ROC-AUC** (not the average — averaging hides collapse)
2. worst-corpus F1
3. false-positive rate
4. recall
5. calibration
6. latency, model size

A model that is excellent on one corpus and poor on the other loses to
one that is consistently adequate.

---

## 9. Semantic regression

`app/ml/semantic_cases.py`. A curated set of 34 hand-built cases (23
legitimate, 11 phishing) with declared expected labels.

**This is not a benchmark.** Corpus metrics cannot detect the failure
mode Phase 2B exhibited, because the corpus simply does not contain
`docs.python.org`. The suite asserts that a documentation URL and a
credential-harvest URL are still distinguishable.

Selection of cases was driven by observed failure modes: documentation
paths, repository URLs, wiki articles with underscores, university
portals, numeric-ID paths, and long legitimate slugs.

---

## 10. Reproducibility

`random_state = 42` throughout; environment and timestamps in
`results/phase2c/environment.json`; corpus audits with SHA-256 checksums
in `datasets/manifests/`.

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.\.venv\Scripts\python.exe -m scripts.run_phase2c_experiment
```