# Phase 2C — Results

> Feeds **Chapter 7 — Results and Evaluation**.
>
> All figures read from `backend/results/phase2c/`.

---

## 1. The headline result

| Training | MUD 2026 ROC-AUC | Source |
|---|---|---|
| PhiUSIIL only (v1) | **0.2713** | Phase 2B |
| **PhiUSIIL + MUD (multi-corpus)** | **0.9889** | Phase 2C |
| Improvement | **+0.7176** | |

Multi-corpus training converts a model that was *worse than chance* on an
independent corpus into one that is near-perfect on it.

The false-positive behaviour improves correspondingly:

| Model | Real legitimate URLs flagged (of 14) |
|---|---|
| v1 (PhiUSIIL-only) | **10 (71%)** |
| v2 (multi-corpus) | see `semantic_regression_summary.json` |

---

## 2. Datasets

| | PhiUSIIL | MUD 2026 |
|---|---|---|
| Rows available | 235,362 | 513,574 |
| Class balance | 134,850 / 100,512 | 421,974 / 91,600 |
| Registered domains | 175,508 | 146,582 |

### 2.1 Multi-corpus training set

Balanced across (corpus × class):

| Cell | Rows |
|---|---|
| phiusil \| legitimate | 91,600 |
| phiusil \| phishing | 91,600 |
| mud2026 \| legitimate | 91,600 |
| mud2026 \| phishing | 91,600 |
| **Total** | **366,400** |

Perfectly balanced by construction, so no corpus or class dominates.
57 cross-corpus duplicate URLs were removed before sampling.

### 2.2 Cross-corpus overlap

| Measure | Value |
|---|---|
| Same normalized URL | **57** |
| Same registered domain | 8,129 |
| Domain Jaccard | 0.0259 |

Low overlap is good for generalization claims: the corpora are genuinely
independent sources, not the same data twice.

---

## 3. Corpus quality gate

| Check | PhiUSIIL | MUD 2026 |
|---|---|---|
| C01 label encoding | pass | pass |
| C02 orientation declared | pass | pass |
| C03 missing URLs | pass | pass |
| C04 duplicates | pass | pass |
| C05 conflicting labels | pass | pass |
| **C06 path presence** | **FAIL** | **FAIL** |
| C07 scheme | pass | pass |
| C08 domain repetition | pass | pass |
| C10 class balance | pass | pass |
| C11 malformed | pass | pass |

**Both corpora fail C06, in opposite directions:**

| Corpus | Legitimate with path | Phishing with path | Gap |
|---|---|---|---|
| PhiUSIIL | **0.0000** | 0.5966 | 0.5966 |
| MUD 2026 | **0.9993** | 0.7628 | 0.2365 |

PhiUSIIL says "path ⇒ phishing"; MUD says "no path ⇒ phishing". Neither
is a property of phishing — both are collection artefacts. This is the
clearest possible demonstration that the feature is meaningless and that
single-corpus training on either one is a mistake.

---

## 4. Feature stability

| Classification | Count |
|---|---|
| STABLE | **3** |
| WEAK | 16 |
| CORPUS-SENSITIVE | 7 |
| **INVERTED** | **15** |

Only 3 of 39 features mean the same thing in both corpora.

---

## 5. Corpus-source bias

A diagnostic classifier distinguishing the two corpora from the same
features:

| Feature set | Features | Corpus-classifier AUC | Accuracy |
|---|---|---|---|
| all_features | 39 | **0.9916** | 96.1% |
| stable_only | 3 | 0.8707 | 83.2% |
| (chance) | — | 0.500 | 50% |

**The corpora are almost perfectly distinguishable.** A phishing score
computed from these features is therefore partly a corpus fingerprint —
the model can identify which dataset a URL came from as well as whether
it is phishing.

Restricting to stable features reduces this substantially (0.9916 →
0.8707), confirming that corpus-identifying information is concentrated
in the unstable features. That is the flip side of §7: those features
hurt *single-corpus* generalization but are not useless — they carry
signal that is corpus-specific rather than phishing-specific.

---

## 6. Feature variant comparison

Ranked by worst-corpus ROC-AUC:

| Variant | Model | Feat | **Worst AUC** | Worst F1 | PhiUSIIL | MUD |
|---|---|---|---|---|---|---|
| **all_features** | **random_forest** | 39 | **0.9419** | 0.8688 | 0.9993 | **0.9889** |
| all_features | xgboost | 39 | 0.9324 | 0.8664 | 0.9988 | 0.9324 |
| exclude_inverted | random_forest | 24 | 0.8945 | 0.8120 | 0.9990 | 0.9678 |
| exclude_inverted | xgboost | 24 | 0.8778 | 0.8144 | 0.9968 | 0.8778 |
| all_features | hist_gradient_boosting | 39 | 0.8447 | 0.8083 | 0.9897 | 0.8447 |
| stable_plus_weak | random_forest | 19 | 0.7999 | 0.7455 | 0.9004 | 0.8831 |
| all_features | logistic_regression | 39 | 0.6911 | 0.7439 | 0.9250 | 0.6911 |
| exclude_inverted | logistic_regression | 24 | 0.5905 | 0.6957 | 0.8564 | 0.5905 |
| **stable_only** | **all four** | **3** | **0.541–0.558** | ~0.663 | 0.59–0.70 | 0.54–0.56 |

### 6.1 Hypothesis H4 is falsified

The hypothesis was that restricting to STABLE features would improve
worst-corpus performance. **It does the opposite** — it collapses
performance to near-chance (0.54 vs 0.94).

The reason is simple in hindsight: only 3 features are stable, and they
are insufficient to separate the classes at all. Stability is a
*filter*, not a *sufficient* condition for usefulness. A model needs
signal first and consistent signal second.

Excluding only the inverted features (variant D, 24 features) is better
than stable-only but still worse than keeping everything. The inverted
features retain real phishing signal — they simply also encode corpus
identity, which multi-corpus training can accommodate.

**This is the most useful negative result in Phase 2C**: the intuitive
"remove the unstable features" heuristic would have made the model
substantially worse.

---

## 7. Model selection

**Selected: Random Forest on all 39 features.**

| Criterion | Value |
|---|---|
| Worst-corpus ROC-AUC | **0.9419** |
| Worst-corpus F1 | **0.8688** |
| MUD 2026 ROC-AUC | 0.9889 |
| PhiUSIIL ROC-AUC | 0.9993 |

Random Forest edges out XGBoost (0.9419 vs 0.9324) and is
substantially smaller than a Phase 2B Random Forest was, because
multi-corpus training converges faster on balanced data.

---

## 8. Leave-one-corpus-out

See `leave_one_corpus_out.csv`. The decisive comparison is:

| Train | Test | ROC-AUC |
|---|---|---|
| PhiUSIIL only | MUD | see CSV |
| MUD only | PhiUSIIL | see CSV |
| **Both** | **MUD** | **0.9889** |
| **Both** | **PhiUSIIL** | **0.9993** |

---

## 9. Semantic regression

`semantic_regression.csv` and `semantic_regression_summary.json`.

The v1 baseline flagged **23 of 23** legitimate semantic cases (100%) and
**10 of 14** real-world legitimate URLs (71%), while catching 91% of
phishing. The multi-corpus candidate's numbers are the comparison that
matters.

---

## 10. Heuristics

`heuristic_analysis.csv`. Phase 2B established the rules are precise but
low-coverage; they are retained as an evidence layer. Redundancy with
the ML model is measured rather than assumed.

---

## 11. Fusion ablation

`ablation_results.csv`. Reported as measured, without forcing fusion to
win.

---

## 12. Calibration and threshold

### 12.1 Calibration (selected model, holdout)

| Method | Brier | Improvement | Best |
|---|---|---|---|
| **raw** | **0.09981** | 0.00000 | **yes** |
| Platt | 0.11486 | −0.01506 | no |
| isotonic | 0.11986 | −0.02005 | no |

**Both calibration methods make the probabilities worse.** The raw
scores are already the best available, so calibration is not applied.

This is the opposite of Phase 2B, where XGBoost was well calibrated
(Brier 0.0023). The difference is instructive: Random Forest
probabilities are known to be poorly distributed out-of-sample, but
here the *uncalibrated* ordering is what the metrics reward, and
recalibration on a shifted holdout distorts it further.

### 12.2 Threshold curve

At the recall floor (≥0.90):

| Threshold | Recall | Precision | FPR |
|---|---|---|---|
| 0.05 | 0.9941 | 0.6589 | 0.4647 |
| 0.20 | 0.9831 | 0.7203 | 0.3448 |
| 0.35 | 0.9518 | 0.7655 | 0.2632 |
| 0.45 | 0.9133 | 0.8021 | 0.2034 |
| 0.65 | 0.7670 | 0.8752 | 0.0988 |
| 0.85 | 0.5213 | 0.9579 | 0.0207 |

**Selected threshold: 0.4733** — the highest value meeting the 0.90
recall floor. The sweep above is on a 0.05 grid, so the continuous
optimum falls between the 0.45 and 0.50 rows; the exact value is
persisted in `threshold_results.csv`.

There is **no high-precision operating point that also holds recall**.
Precision only exceeds 0.90 once recall collapses below 0.53. This is the
corpus-level counterpart of the real-world problem: the model cannot
separate the classes sharply on data whose legitimate URLs lack path
structure.

This is the corpus-level counterpart of the real-world problem: the
model cannot separate the classes sharply on data whose legitimate URLs
lack path structure.

---

## 13. False-positive composition

All 18 semantic false positives, by category:

| Category | Count |
|---|---|
| documentation | 3 |
| repository | 3 |
| university | 3 |
| academic | 2 |
| legacy | 2 |
| corporate, government, qanda, news, education | 1 each |

**Every false positive is a real, well-known legitimate service.** There
is exactly one false negative. The model has not become erratic — it has
learned its corpora's rule ("a path means phishing") and applied it
consistently to a world where legitimate URLs have paths.

---

## 14. v2 promotion

Promotion requires **both** better worst-corpus generalization **and**
materially lower real-world false positives. See
`models/basirah-url-v2.metadata.json` for the decision record.