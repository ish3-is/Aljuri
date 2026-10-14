# Phase 2B — Evaluation

> Feeds **Chapter 7 — Results and Evaluation**.
>
> Every number here is read from `backend/results/phase2b/`. Nothing is
> transcribed by hand.

---

## 1. Experimental setup

| Parameter | Value |
|---|---|
| Training corpus | PhiUSIIL (UCI id 967), 235,362 rows |
| Feature extractor | BASIRAH production extractor, v2.1.0 |
| Features computed | 41 |
| Features used as model input | **39** (2 excluded, §2) |
| Split strategies | Random stratified + grouped-by-registered-domain |
| Train / val / test | 70 / 15 / 15 |
| Seed | 42 |
| Threshold tuning | Validation fold only |
| Calibration fitting | Validation fold only |

---

## 2. The exclusion of `uses_https` and `uses_http`

This is the most consequential methodological decision in Phase 2B, so it
is stated before any result.

### 2.1 What was measured

| Corpus | P(https \| phishing) | P(https \| legitimate) | Lift | Direction |
|---|---|---|---|---|
| PhiUSIIL | 1.0000 | 0.4863 | **+2.06** | HTTPS ⇒ phishing |
| MUD 2026 | 0.8198 | 0.9209 | **−0.89** | HTTPS ⇒ legitimate |

**The association inverts between corpora.** A feature whose relationship
to the label reverses depending on which dataset you ask is not measuring
phishing — it is measuring collection methodology. PhiUSIIL's phishing
URLs happen to be exclusively HTTPS; MUD's are 82% HTTPS.

### 2.2 Why it mattered

With the scheme features present, the model's **top-ranked feature was
`uses_https`**. Trained on PhiUSIIL, it learned "HTTPS ⇒ phishing" with
almost perfect confidence, then applied that rule backwards on real-world
data.

### 2.3 Effect of removal

Measured on a 120k-row sample, grouped split, threshold 0.5
(`results/phase2b/shortcut_feature_experiment.csv`):

| Variant | Model | In-domain AUC | External AUC | External recall |
|---|---|---|---|---|
| with scheme | logistic_regression | 0.9978 | 0.6818 | 0.127 |
| with scheme | random_forest | 0.9980 | 0.6005 | 0.053 |
| with scheme | xgboost | 0.9975 | 0.6589 | 0.050 |
| with scheme | hist_gradient_boosting | 0.9980 | 0.6424 | 0.054 |
| **no scheme** | logistic_regression | 0.9956 | 0.6234 | 0.167 |
| **no scheme** | random_forest | 0.9972 | 0.6072 | 0.013 |
| **no scheme** | **xgboost** | **0.9981** | **0.7477** | 0.039 |
| **no scheme** | hist_gradient_boosting | 0.9979 | 0.6739 | 0.054 |

Removing the features **cost essentially nothing in-domain** (XGBoost
0.9975 → 0.9981, i.e. slightly better) and **improved cross-dataset AUC
by 8.9 points** for the best model.

### 2.4 What this does and does not claim

It does **not** claim HTTPS is useless for phishing detection. It claims
that *in these corpora*, HTTPS is a collection artefact, so a model must
not be permitted to rely on it. The features remain computed and remain
visible in the product's explanation panel — they are simply not model
inputs.

---

## 3. Model comparison — random split

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | FPR | Inference (ms) | Size (MB) |
|---|---|---|---|---|---|---|---|---|
| hist_gradient_boosting | 0.9581 | 0.9998 | 0.9020 | 0.9484 | 0.9983 | 0.0001 | 89.99 | 0.52 |
| logistic_regression | 0.9579 | 0.9995 | 0.9020 | 0.9482 | 0.9974 | 0.0003 | 4.10 | <0.01 |
| xgboost | 0.9579 | 1.0000 | 0.9014 | 0.9481 | 0.9990 | 0.0000 | 38.69 | 1.39 |
| random_forest | 0.9554 | 0.9997 | 0.8957 | 0.9449 | 0.9986 | 0.0002 | 133.58 | 49.62 |

*Accuracy sits near 0.958 rather than 0.99 because the operating
threshold is tuned to a 0.90 recall floor (§6), not left at 0.5.*

---

## 4. Model comparison — grouped-domain split

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | FPR | Inference (ms) | Size (MB) |
|---|---|---|---|---|---|---|---|---|
| **random_forest** | 0.9549 | 0.9988 | 0.8746 | 0.9326 | 0.9979 | 0.0006 | 149.04 | 49.62 |
| **xgboost** | 0.9541 | **1.0000** | 0.8715 | 0.9313 | 0.9983 | **0.0000** | **31.13** | 1.39 |
| hist_gradient_boosting | 0.9541 | 0.9988 | 0.8725 | 0.9314 | 0.9978 | 0.0006 | 89.99 | 0.52 |
| logistic_regression | 0.9518 | 0.9988 | 0.8662 | 0.9278 | 0.9973 | 0.0006 | 4.10 | <0.01 |

---

## 5. The "99% accuracy may be misleading" analysis

### 5.1 Random vs grouped: the leakage question

| Model | Random accuracy | Grouped accuracy | Δ |
|---|---|---|---|
| random_forest | 0.9554 | 0.9549 | −0.0005 |
| xgboost | 0.9579 | 0.9541 | −0.0038 |
| hist_gradient_boosting | 0.9581 | 0.9541 | −0.0040 |
| logistic_regression | 0.9579 | 0.9518 | −0.0061 |

**The drop is 0.05–0.6 percentage points.** That is small.

Interpretation: the model is **not** relying on domain memorisation. If
it were, forcing unseen domains into the test fold would produce a
collapse, not a sub-point dip. PhiUSIIL contains 175,508 distinct
registered domains across 235,362 rows — most appear once, so there is
little to memorise.

The leakage-control machinery was built, the assertion passes with an
empty intersection, and the conclusion is that it did not need to rescue
the result — it confirmed it. This is the **opposite** of the collapse
the brief anticipated, reported as measured.

### 5.2 Where a high score genuinely does mislead

Not through in-domain leakage. Two other ways:

**Class imbalance.** 57% of the corpus is phishing, so the
majority-class baseline is already ~0.57. At threshold 0.5 every model
reaches ~0.998 (see `ablation_results.csv`), and that figure mostly
reflects the prior, not capability.

**Threshold choice.** Accuracy near 0.96 at the tuned operating point
reflects a deliberate decision to hold recall at 0.90 rather than
accept more false alarms. Neither number is "the" accuracy:

- At threshold 0.5: how separable are the classes? → ~0.998
- At the operating threshold: how does it behave? → ~0.954 at 90% recall

**The genuinely misleading high score is the cross-dataset one.** See
`phase2b-generalization.md`, where the same model scores **AUC 0.271**
on an independent corpus — worse than chance.

---

## 6. Calibration and threshold

### 6.1 Calibration (grouped-domain test fold)

| Model | Brier raw | Brier Platt | Brier isotonic | Best |
|---|---|---|---|---|
| logistic_regression | 0.00843 | 0.00541 | **0.00478** | isotonic |
| random_forest | 0.01061 | 0.00970 | **0.00968** | isotonic |
| xgboost | 0.00227 | **0.00226** | 0.00232 | Platt |
| hist_gradient_boosting | 0.00970 | 0.00749 | **0.00738** | isotonic |

XGBoost is already very well calibrated (Brier 0.0023). The tree models
benefit modestly from post-hoc calibration. Isotonic improves three of
four; **for the selected model (XGBoost) raw probabilities are already
the best choice**, so calibration is not applied by default.

### 6.2 Selected thresholds (validation fold only)

| Model | Threshold | Recall | Precision |
|---|---|---|---|
| logistic_regression | 0.8446 | 0.9001 | 0.9991 |
| hist_gradient_boosting | 0.8710 | 0.9003 | 0.9994 |
| random_forest | 0.9067 | 0.9004 | 0.9994 |
| **xgboost** | **0.9965** | 0.9000 | **1.0000** |

All models are extremely confident when correct, so the optimal
operating point sits far above the default 0.5, which would accept many
false alarms.

---

## 7. Ablation: does fusion help?

Grouped-domain split, F1:

| Configuration | F1 | Recall | ROC-AUC |
|---|---|---|---|
| xgboost + heuristics @90% ML | 0.9966 | 0.9946 | 0.9983 |
| **xgboost only** | **0.9966** | 0.9946 | 0.9983 |
| xgboost + heuristics @80% ML | 0.9962 | 0.9937 | 0.9983 |
| logistic + heuristics @80% ML | 0.9928 | 0.9892 | 0.9973 |
| **heuristics only** | **0.0729** | 0.0378 | 0.6779 |

**Fusion does not beat ML alone.** At a 90% ML weight the two are
identical; at lower weights the heuristics drag performance down.

Heuristics alone reach AUC 0.678 — better than chance, so they carry
real signal, but nowhere near the model.

Reported as measured. The brief explicitly forbids forcing combined
fusion to win.

---

## 8. Feature importance

After excluding the scheme features, the dominant signal families are
URL/path length, path structure, subdomain depth and suspicious-TLD
membership. Full table in `results/phase2b/feature_importance.csv`.

**Importance is not causation** — and §5 of `phase2b-generalization.md`
is the concrete demonstration: the length features rank highest because
they separate PhiUSIIL's classes well, and 20 of 39 features have an
inverted association in an independent corpus.

---

## 9. Robustness slices

From `results/phase2b/robustness_slices.csv`. Slices below 200 rows are
omitted, since a metric on a handful of examples is noise.

## 9. What this evaluation does not establish

1. **Not a real-world accuracy claim.** PhiUSIIL is a research corpus, not
   a sample of live traffic. See `phase2b-generalization.md`.
2. **No temporal validation.** A random split cannot measure decay on
   newly-registered domains.
3. **URL-string only.** Page content, redirects, certificates and DNS
   are all invisible.
4. **One corpus, one language mix.** No Arabic-language phishing
   coverage beyond the small keyword lexicon.
