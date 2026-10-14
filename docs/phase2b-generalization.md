# Phase 2B — Cross-Dataset Generalization

> The most important experimental result in the project.
>
> An in-domain score of 0.998 AUC means very little on its own. This
> document reports where the model **breaks** when moved to data it was
> not trained on, why, and how much of the feature set is implicated.

---

## 1. Experimental question

> Does the model perform well only on the corpus it was trained on, or
> does it generalize to an independent dataset?

The answer is **no**, and the reason is quantified below rather than
speculated about.

---

## 2. Two corrections made before these results were trustworthy

Both were found by Phase 2B and both are recorded because they are
methodologically instructive.

### 2.1 Label orientation (fatal, fixed)

PhiUSIIL encodes **`label 1 = legitimate`, `label 0 = phishing`** — the
inverse of the near-universal convention. Stated on the UCI dataset
page: *"Label 1 corresponds to a legitimate URL, label 0 to a phishing
URL"*, and repeated in the peer-reviewed literature — Frontiers in
Computer Science (2026): *"The original PHIUSIIL labels follow a
convention in which 1 denotes legitimate and 0 denotes phishing. We
invert this so that 1 denotes phishing."*

The first Phase 2B run assumed the convention. The resulting model
scored:

| URL | Score |
|---|---|
| `google.com` | 99.9% phishing |
| `paypal.com` | 99.9% phishing |
| `secure-login-account-update.example.com` | 0% |

**No metric revealed this.** Every AUC, F1 and accuracy figure was
computed against the same inverted labels, so the model reported 0.998
while being exactly backwards.

**Fixes applied:**
- `detect_label_orientation()` now returns `0` for a bare numeric label
  column instead of assuming the convention.
- `LabelOrientationError` aborts the audit when orientation is unstated.
- `label_orientation=-1` is passed explicitly for PhiUSIIL.
- `tests/test_phase2b_semantics.py` asserts on **meaning**, not metrics:
  known-legitimate hosts must score low, blatant phishing must score
  high, and phishing must outscore legitimate. These catch any future
  inversion.

### 2.2 Feature-association inversion

`uses_https` / `uses_http` had an inverted class association and were
excluded from model input. See `phase2b-evaluation.md` §2.

---

## 3. Experimental design

| Property | Training corpus | External corpus |
|---|---|---|
| Name | PhiUSIIL | Malicious URL Detection Enhanced 2026 |
| Source | UCI id 967 | Kaggle |
| Rows used | 235,362 | 513,574 |
| Classes used | legitimate / phishing | **benign and phishing only** |
| Registered domains | 175,508 | 146,582 |
| Domains shared with training | — | **92,006** |

### 3.1 Why defacement and malware were excluded

MUD is a **four-class** corpus. Only `benign` and `phishing` are
commensurable with a phishing-vs-legitimate task.

| Excluded class | Rows | Reason |
|---|---|---|
| defacement | 95,285 | Site hijacking — a different threat model |
| malware | 23,577 | Malware distribution — a different threat model |

Also excluded: 102 URLs labelled both classes, 35 duplicates, 165
malformed. All counted in `results/phase2b/dataset_summary.json`.

---

## 4. Result

### 4.1 Corrected model

| Metric | In-domain (grouped) | External | Gap |
|---|---|---|---|
| ROC-AUC | **0.9983** | **0.2713** | **−0.727** |
| Accuracy | 0.9541 | 0.1591 | −0.795 |
| Precision | 1.0000 | 0.1616 | −0.838 |
| Recall | 0.8715 | 0.8872 | +0.016 |
| F1 | 0.9313 | 0.2734 | −0.658 |

### 4.2 Reading an AUC below 0.5

**AUC 0.271 is worse than a coin flip.** This is not ordinary
degradation. A model that generalised poorly would land near 0.5.
Scoring *systematically below* 0.5 means its decision boundary is
**inverted** on this data — it ranks MUD's benign URLs above its
phishing URLs.

That is the signature of features whose relationship to the label has
reversed, which §5 measures directly.

---

## 5. Root cause: 20 of 39 features are inverted

`scripts/audit_feature_directions.py` compares, for every model input,
the mean value on phishing minus the mean on benign — in both corpora.
Full output: `results/phase2b/feature_direction_audit.csv`.

| Result | Count |
|---|---|
| Association agrees across corpora | 19 / 39 |
| **Association is OPPOSITE** | **20 / 39** |

### 5.1 The strongest inversions

| Feature | PhiUSIIL (phish − benign) | MUD (phish − benign) |
|---|---|---|
| `url_length` | **+16.69** | **−14.11** |
| `path_length` | **+7.58** | **−20.24** |
| `query_length` | +4.68 | −0.60 |
| `digit_count` | +3.88 | −1.07 |
| `registered_domain_length` | −2.11 | **+2.62** |
| `slash_count` | +0.93 | −1.23 |

Also inverted: `hyphen_count`, `underscore_count`,
`suspicious_keyword_count`, `brand_token_count`, `digit_ratio`,
`letter_ratio`, `encoded_ratio`, `is_long_path`,
`is_excessive_hyphen`, `is_high_digit_ratio`, `has_port`,
`encoded_char_count`, `query_param_count`, `path_entropy`.

### 5.2 Interpretation

In PhiUSIIL, phishing URLs are **long, deep, hyphen-heavy brand
impersonations** — `secure-login-account-update.example.com`.

In MUD, phishing URLs are **short and flat**, while its benign class
contains long, parameter-heavy tracking URLs.

The model learned "long + deep + hyphenated ⇒ phishing" — a true
statement about PhiUSIIL and close to its opposite about MUD. Half the
feature set points the wrong way, which is enough to push AUC below
chance.

**This is not a model bug. It is a difference in what the two corpora
call phishing.**

---

## 6. Honest assessment

| Claim | Supported? |
|---|---|
| Separates phishing from legitimate **within PhiUSIIL** | **Yes** — AUC 0.998, grouped, leakage-free |
| Does so without domain memorisation | **Yes** — grouped split costs ~0.4 points |
| Behaves sanely on known hosts | **Yes**, post-correction |
| Generalises to an independent corpus | **No** — AUC 0.27 |
| Would perform acceptably on live traffic | **No evidence** |

The model is a **valid research artefact with a severe, measured, and
now fully explained generalization gap**. Presenting the in-domain 0.998
without this document would be misleading.

---

## 7. What would close the gap

Ordered by expected value:

1. **Multi-corpus training.** Half the feature set disagrees between
   corpora; training on both is the direct remedy.
2. **Per-feature direction audit as a standard gate.** Phase 2B found
   the scheme inversion by accident, then wrote
   `audit_feature_directions.py`, which immediately found 20 inverted
   features. That check should run on every model before it ships.
3. **Corpus-balanced reporting.** Per-corpus metrics, never a single
   number.
4. **Temporal split.** PhiUSIIL is 2020, MUD 2026 — the shift is
   unmeasured and probably large.
5. **Character n-grams**, which may transfer better than length ratios.
6. **Drop or reweight features whose direction is unstable.** 20 of 39
   are currently a liability.

---

## 8. Product consequence

BASIRAH must not present a single confidence number as if universally
calibrated. Two changes follow directly:

1. **State the model's provenance and its measured generalization.**
2. **Treat the heuristic engine as the transparent floor**, not as a
   performance win — its rules do not depend on corpus-specific
   statistics. Their measured behaviour is in
   `results/phase2b/heuristic_rule_analysis.csv`.
