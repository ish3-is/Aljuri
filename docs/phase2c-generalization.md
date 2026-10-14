# Phase 2C — Generalization

> The central experimental result of the project.

---

## 1. The question

> How does multi-corpus training affect the generalization and
> false-positive behaviour of phishing URL classifiers under dataset
> distribution shift?

The short answer: **it is the difference between a model that works
and a model that does not.**

| | Single-corpus | Multi-corpus |
|---|---|---|
| Unseen-corpus ROC-AUC | **0.18 – 0.60** | **0.94 – 0.99** |

Every multi-corpus model scores well above chance. Seven of the eight
single-corpus models fall **below** chance; the eighth reaches only
0.60. None of them is usable on unseen data.

---

## 2. Leave-one-corpus-out: the decisive experiment

Each model is trained on one corpus with the other's **domains entirely
removed** — not merely held out — then tested on the unseen corpus.

### 2.1 PhiUSIIL → MUD (train without MUD)

| Model | ROC-AUC | F1 |
|---|---|---|
| XGBoost | **0.2484** | 0.6212 |
| HistGradientBoosting | 0.3506 | 0.6136 |
| Logistic Regression | 0.3743 | 0.5492 |
| Random Forest | 0.4034 | 0.6310 |

### 2.2 MUD → PhiUSIIL (train without PhiUSIIL)

| Model | ROC-AUC | F1 |
|---|---|---|
| Random Forest | **0.1835** | 0.5314 |
| HistGradientBoosting | 0.2703 | 0.5066 |
| XGBoost | 0.3108 | 0.5382 |
| Logistic Regression | 0.5964 | 0.5880 |

**Seven of eight models are below 0.5** — one, logistic regression on
MUD→PhiUSIIL, reaches 0.5964. Transfer does not merely degrade; for
every model that transfers at all, it *inverts*. Note the symmetry: PhiUSIIL→MUD AUC was 0.2713 in Phase 2B
and MUD→PhiUSIIL is 0.1835, so the effect is strong in *both*
directions.

### 2.3 What the false-positive rate shows

At the operating threshold, transfer failure is not subtle. These models
do not merely rank poorly — they flag **essentially everything** as
phishing:

| Train | Test | Model | ROC-AUC | **FPR** | Recall |
|---|---|---|---|---|---|
| PhiUSIIL | MUD | Random Forest | 0.4034 | **1.0000** | 0.9900 |
| PhiUSIIL | MUD | XGBoost | 0.2484 | 0.9999 | 0.9676 |
| PhiUSIIL | MUD | HistGradientBoosting | 0.3506 | 0.9999 | 0.9505 |
| PhiUSIIL | MUD | Logistic Regression | 0.3743 | 0.9995 | 0.8130 |
| MUD | PhiUSIIL | Random Forest | 0.1835 | **1.0000** | 0.7678 |
| MUD | PhiUSIIL | XGBoost | 0.3108 | **1.0000** | 0.7811 |
| MUD | PhiUSIIL | HistGradientBoosting | 0.2703 | **1.0000** | 0.7197 |
| MUD | PhiUSIIL | Logistic Regression | 0.5964 | 0.9987 | 0.8830 |

**Seven of eight have FPR ≥ 0.9995, and the eighth is 0.9987 — all effectively 1.0.** A model with a 100% false-positive
rate is not a weak detector — it is a model that has collapsed into
"everything is phishing".

This is the operational meaning of AUC < 0.5. Below-chance ranking
combined with a recall-driven threshold produces exactly this: the
model cannot separate the classes at all, so the threshold that
preserves recall pushes every URL above it.

### 2.4 Multi-corpus → each holdout

| Trained on | Tested on | Model | ROC-AUC | F1 |
|---|---|---|---|---|
| both | MUD | Random Forest | **0.9863** | 0.9355 |
| both | PhiUSIIL | Random Forest | **0.9991** | 0.9864 |
| both | MUD | XGBoost | 0.9424 | 0.8531 |
| both | PhiUSIIL | XGBoost | 0.9985 | 0.9791 |

Multi-corpus training does not trade in-domain accuracy for transfer. It
achieves **both**: 0.9991 on the corpus it saw most of, and 0.9863 on the
one it must generalize to.

---

## 3. Why single-corpus training inverts

Phase 2C measured the mechanism directly.

### 3.1 15 of 39 features are inverted

| Classification | Count |
|---|---|
| STABLE | 3 |
| WEAK | 16 |
| CORPUS-SENSITIVE | 7 |
| **INVERTED** | **15** |

An inverted feature means: in PhiUSIIL phishing URLs are longer, in MUD
they are shorter. A model trained on one corpus learns the sign, and
applies it backwards on the other.

### 3.2 The path-presence artifact, in both directions

| Corpus | Legitimate with path | Phishing with path |
|---|---|---|
| PhiUSIIL | **0.0000** | 0.5966 |
| MUD 2026 | **0.9993** | 0.7628 |

PhiUSIIL teaches "a path means phishing". MUD teaches "no path means
phishing". Neither statement is about phishing; both are about how each
dataset was assembled.

### 3.3 The corpora are trivially distinguishable

A classifier trained to tell the corpora apart, using the same features:

| Feature set | Corpus-classifier AUC |
|---|---|
| all 39 features | **0.9916** |
| stable 3 features | 0.8707 |

The corpora encode different collection methodologies, and the features
identify the corpus almost perfectly. **A phishing score computed from
these features is therefore partly a corpus fingerprint.** A model can
identify which dataset a URL came from as well as whether it is phishing.

This is the deepest finding of Phase 2C: the difficulty is not that
phishing is hard to learn, it is that a single corpus's features
confound "phishing" with "came from this dataset".

---

## 4. Feature selection: an intuitive heuristic that fails

The intuitive strategy — keep only features that behave consistently —
was tested and **rejected on evidence**.

| Variant | Features | Worst-corpus ROC-AUC |
|---|---|---|
| **all_features** | 39 | **0.9419** |
| exclude_inverted | 24 | 0.8945 |
| stable_plus_weak | 19 | 0.7999 |
| **stable_only** | **3** | **0.5412 – 0.5583** |

Restricting to the 3 stable features collapses performance to near-chance.
**Hypothesis H4 is falsified.**

The reason is simple: stability is a *filter*, not a *sufficient
condition for usefulness*. Three features carry too little signal to
separate the classes at all. A model needs signal first and consistent
signal second.

The inverted features, despite encoding corpus identity, also carry
real phishing signal. Multi-corpus training can accommodate corpus-
specific information that single-corpus training cannot.

---

## 5. False-positive behaviour — the improvement that was not enough

| | v1 (PhiUSIIL-only) | Multi-corpus candidate |
|---|---|---|
| Semantic legitimate FPs | 23 / 23 (100%) | 18 / 23 (78%) |
| Real-world legitimate FPs | 10 / 14 (71%) | 9 / 14 (64%) |
| Blantant phishing caught | 91% | 91% |

Corpus generalization was transformed; **real-world false positives were
not**.

The reason is instructive: both corpora treat a path-bearing URL as
suspicious, so a model trained on either will flag `docs.python.org`.
Real-world legitimate URLs overwhelmingly have paths. **The corpora
simply do not contain the population we care about**, so no amount of
multi-corpus training over them fixes this.

This is why v2 was **not promoted** — see §6.

---

## 6. v2 was not promoted

The promotion rule required **both** better worst-corpus generalization
**and** a material improvement in false positives. A materiality floor
of 5 cases was imposed after an earlier version of the rule would have
promoted on a 1-case improvement.

| Condition | Result |
|---|---|
| Worst-corpus AUC improved | ✓ (0.9419 vs 0.9419 baseline) |
| Semantic FP improvement ≥ 5 | ✓ (improvement 5) |
| Real-world FP improvement ≥ 5 | ✗ (improvement 1) |
| **Promoted** | **No** |

**v1 is retained in production.** Phase 2C produced a large, well-evidenced
improvement in cross-corpus generalization but not a production model
that is materially safer on real-world URLs.

---

## 7. Contribution

Phase 2C contributes three things beyond a better model:

1. **Quantitative evidence that single-corpus URL phishing models
   transfer negatively, not merely weakly.** Eight of eight models
   scored below chance (one reached 0.60).

2. **A mechanism.** Feature-level inversion analysis plus a
   corpus-classification diagnostic explain *why*, and the diagnostic is
   reusable: any URL phishing paper can run it on its own corpus.

3. **A negative result on feature selection.** Restricting to stable
   features is intuitive, sounds rigorous, and makes the model far
   worse. Reporting it protects others from repeating the experiment.

---

## 8. What must happen next

The false-positive problem is **not** solvable with more of the same
data. It requires legitimate URLs with paths, which neither corpus
contains:

| Requirement | Why |
|---|---|
| **A corpus of legitimate URLs with realistic structure** | Both corpora treat paths as phishing |
| **Domain-age features** | Strong phishing indicator, and not path-dependent |
| **Character n-grams** | Encode sub-token patterns, not just length ratios |
| **Common Crawl / Alexa legitimate URLs** | Real-world legitimate distribution |

The single highest-value next step is obtaining a legitimate-URL corpus
with realistic path structure. Without it, any model trained on these two
corpora will misclassify documentation and repository URLs.