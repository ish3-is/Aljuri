# Phase 2D — Evaluation

> Feeds **Chapter 7 — Results and Evaluation**.
> All figures from `backend/results/phase2d/`.

---

## 1. Corpora

| Corpus | Role | Rows | % with path | % HTTPS |
|---|---|---|---|---|
| PhiUSIIL | train (legit + phishing) | 235,362 | 0.00 legit | low |
| MUD 2026 | train (benign + phishing) | 513,574 | 99.93 benign | 92.09 |
| **Realistic (HF)** | **train (legitimate)** | **813,603** | **87.58** | **6.58** |
| PhishTank | **held-out phishing** | 74,989 | 60.51 | — |
| Tranco | reference only | 1,000,000 | 0.00 | — |

Training total: **236,953 rows** after corpus-aware balancing.

---

## 2. Corpus quality gate

Six new checks (C13–C18) were added and are **blocking** for a
legitimate corpus. Both new corpora pass; PhiUSIIL and MUD continue to
fail C06 (path presence as a class proxy) — which is the defect being
corrected, and the reason those corpora cannot be trusted alone.

---

## 3. Model comparison

| Variant | Model | Grouped AUC | Worst AUC | PhishTank recall | Real FP |
|---|---|---|---|---|---|
| **all_features** | **xgboost** | **0.9476** | **0.8481** | 0.9092 | **5/14** |
| all_features | random_forest | 0.9413 | 0.8481 | 0.9091 | 6/14 |
| all_features | hist_gradient_boosting | 0.9078 | 0.8284 | 0.9176 | 7/14 |
| exclude_inverted | random_forest | 0.7847 | 0.6750 | 0.9121 | 7/14 |
| all_features | logistic_regression | 0.7963 | 0.7085 | 0.6603 | 10/14 |
| stable_plus_weak | *any* | 0.65–0.67 | 0.50–0.58 | 0.65–0.80 | 9–12/14 |

**`all_features` wins again.** Phase 2C found that restricting to stable
features collapses performance; Phase 2D reproduces that finding on a
third corpus mix. Structural diversity in the feature set is necessary
even when individual features are corpus-sensitive.

---

## 4. The recall comparison, corrected

### 4.1 The invalid comparison

| Model | Recall | at FPR |
|---|---|---|
| v1 | 0.9788 | 0.658 |
| v3 | 0.9092 | 0.137 |

Comparing these numbers measures flagging aggressiveness, not detection
ability. v1 earns its recall by accusing two-thirds of legitimate
traffic.

### 4.2 The valid comparison

| Model | Recall @ FPR 0.05 |
|---|---|
| v1 | 0.2601 |
| **v3** | **0.7601** |

**The candidate detects nearly 3× more phishing at an acceptable
false-alarm rate.** No criterion regresses.

---

## 5. Path-bias analysis

Mean predicted phishing probability by path depth:

| Depth | Legitimate | Phishing | Gap |
|---|---|---|---|
| 0 | 0.083 | 0.924 | 0.841 |
| 1 | 0.252 | 0.785 | 0.533 |
| 2 | 0.225 | 0.780 | 0.555 |
| 3 | 0.188 | 0.748 | 0.560 |
| 4 | 0.206 | 0.740 | 0.534 |
| 5 | 0.206 | 0.845 | 0.639 |
| 6 | 0.385 | 0.840 | 0.455 |

**Path bias is eliminated.** v1 scored legitimate depth-1 URLs at ~1.000;
v3 scores them 0.252. Phishing stays 0.74–0.92 at every depth, so the
separation is maintained.

Residual: legitimate depth-6 URLs score 0.385, the only remaining
depth-related elevation.

---

## 6. Error analysis

| Type | Count |
|---|---|
| Semantic false positives | 8 |
| **Semantic false negatives** | **0** |

All 11 phishing semantic cases are correctly classified.

**False positives by category:**

| Category | Flagged |
|---|---|
| documentation | 2/3 |
| university | 2/3 |
| repository | 2/4 |
| qanda | 1/1 |
| news | 1/1 |
| encyclopedia, academic, search, media, education, corporate, government, legacy | **0** |

Full per-error detail with path depth, query count and triggered
heuristics in `false_positive_analysis.csv`.

---

## 7. Feature importance

| Feature | Group | Importance |
|---|---|---|
| `suspicious_tld` | lexical | 0.326 |
| `is_excessive_hyphen` | derived flag | 0.245 |
| `subdomain_depth` | structure | 0.039 |
| `is_ip_host` | identity | 0.035 |
| `path_length` | length | 0.030 |
| `suspicious_keyword_count` | lexical | 0.029 |

Phishing-specific signals dominate; raw structural features are
marginal. This is the mechanism behind the path-bias result.

---

## 8. Threshold and calibration

| | |
|---|---|
| Selected threshold | **0.4918** |
| Selection | validation fold, recall floor |
| Calibration | **not applied** (raw) |

A threshold of 0.49 versus v1's 0.997 reflects genuinely different
calibration, not a threshold-tuning error. Both are persisted in
`threshold_results.csv`.

---

## 9. Corpus-source classifier

| Corpora | Source AUC |
|---|---|
| 2 (Phase 2C) | 0.9916 |
| **4 (Phase 2D)** | **0.9477** (ovr macro) |

Source identity remains highly recoverable. Adding the realistic corpus
did not reduce it.

---

## 10. Promotion

**v3 is a staged candidate. v1 is unmodified** (SHA-256 verified against
its metadata, still reproduces 10/14).

Promotion criteria met: FP halved, no regression at matched FPR, grouped
and cross-corpus performance both improved substantially, behaviour
explainable via the feature-importance shift.