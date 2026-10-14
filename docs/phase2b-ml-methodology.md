# Phase 2B — ML Methodology

> Feeds **Chapter 5 — Methodology** and the implementation sections of
> **Chapter 6**.
>
> Every figure quoted here is produced by
> `backend/scripts/run_phase2b_experiment.py` and written to
> `backend/results/phase2b/`. Nothing is hand-entered.

---

## 1. Problem statement

Given a URL string, estimate the probability that it is a phishing URL.

Formally, with URL string `u` and label `y ∈ {0, 1}` (0 = legitimate,
1 = phishing):

```
  P(y = 1 | u) = f_θ(u)
```

where `f_θ` is a model operating **only** on features derived from `u`
itself.

### 1.1 Scope decision inherited from Phase 2A

BASIRAH's live pipeline is **URL-string-only**. It parses a URL and never
fetches a page. No HTTP request, no JavaScript execution, no DNS
resolution.

This is a deliberate safety and reproducibility trade-off:

| Property gained | Consequence |
|---|---|
| Cannot be used as an SSRF vector | No request is ever made |
| Deterministic and offline | Same input, same output, always |
| Fast (sub-millisecond) | No network round-trip |
| Reproducible for evaluation | No page state changes between runs |

The constraint propagates into the ML design: **the model may only use
features that exist at inference time.** See §2.2.

---

## 2. Data

Full provenance, integrity checks and cleaning statistics are in
`phase2b-dataset-audit.md`. Summarised:

| Property | PhiUSIIL |
|---|---|
| Rows in file | 235,795 |
| Rows used | 235,362 (99.82%) |
| Class balance | 100,512 legitimate / 134,850 phishing |
| Distinct registered domains | 175,508 |
| Repeated domain families | 5,964 |

---

## 3. Feature extraction

### 3.1 Single source of truth

All 41 features come from one function:

```python
# backend/app/services/feature_extractor.py
extract_features(normalized_url) -> dict[str, float]
```

This is the **same function used in production inference**. There is no
notebook-only extractor and no second implementation. This is enforced
mechanically by the feature schema (§3.3), not by convention.

### 3.2 Feature groups

| Group | Count | Examples |
|---|---|---|
| Length | 5 | `url_length`, `hostname_length`, `path_length` |
| Character counts | 8 | `digit_count`, `hyphen_count`, `dot_count` |
| Composition ratios | 4 | `digit_ratio`, `letter_ratio`, `encoded_ratio` |
| Structure | 7 | `subdomain_depth`, `is_ip_host`, `is_punycode` |
| Obfuscation | 3 | `encoded_char_count`, `double_slash_count` |
| Entropy | 4 | `url_entropy`, `hostname_entropy` |
| Lexical | 3 | `suspicious_keyword_count`, `suspicious_tld` |
| Derived flags | 7 | `is_suspicious_keyword_combo`, `is_long_url` |

### 3.3 The train/serve contract

`app/ml/feature_schema.py` persists:

- the ordered feature list
- the extractor version (`2.0.0`)
- a SHA-256 fingerprint over version **and order**
- per-feature type, group and description

Both training and inference assert the schema matches. A mismatch raises
`FeatureSchemaMismatch` and the model is **refused**.

Order mismatch is handled explicitly because it is the dangerous case: if
two features swap positions, every set-based comparison still passes and
the model silently receives permuted input.

---

## 4. Data leakage control

### 4.1 The problem

PhiUSIIL contains 5,964 registered-domain families appearing more than
once. Under a random split, `login.example.com` may fall in training while
`verify.example.com` falls in testing. The model has then effectively
seen the test domain, and its score measures domain memorisation rather
than learned phishing structure.

### 4.2 Two evaluation strategies

| Strategy | Method | Question answered |
|---|---|---|
| **Random** | `train_test_split`, stratified | Conventional academic setting |
| **Grouped** | `StratifiedGroupKFold` on registered domain | Performance on unseen domains |

Grouping key = registered domain, so `login.example.com`,
`verify.example.com` and `example.com/reset` share the group
`example.com` and cannot be split apart.

### 4.3 Automated leakage assertion

`app/ml/splits.py` raises `DomainLeakageError` and **aborts the
experiment** if any domain appears in two partitions. Verified output:

```json
{
  "statement": "intersection(train_registered_domains, test_registered_domains) == empty",
  "intersection_train_test_count": 0,
  "intersection_train_val_count": 0,
  "intersection_val_test_count": 0,
  "is_empty": true
}
```

The assertion runs in the pipeline itself and in the test suite
(`tests/test_phase2b_leakage.py`), so a regression cannot pass silently.

### 4.4 Additional controls

| Control | Implementation |
|---|---|
| Duplicates | Removed after URL normalisation, before splitting |
| Conflicting labels | Detected and dropped, never guessed |
| Threshold tuning | Validation fold only |
| Calibration fitting | Validation fold only |
| Final test fold | Touched exactly once, for reporting |

---

## 5. Models

Four candidates, chosen to span the interpretability/performance trade-off:

| Model | Rationale |
|---|---|
| Logistic Regression | Fully interpretable coefficients; the interpretable baseline |
| Random Forest | Non-linear, robust, insensitive to feature scaling |
| XGBoost | Strong tabular gradient boosting; Phase 2B requirement |
| HistGradientBoosting | scikit-learn's histogram booster; a second boosting reference |

All use `class_weight="balanced"` / equivalent, because the phishing class
is the majority (57.2%) and an unweighted fit would inherit that prior.

`random_state = 42` throughout.

---

## 6. Risk fusion

```
final_risk = w_ml · ml_risk + w_heuristic · heuristic_risk
trust_score = 100 − final_risk
```

Weights evaluated: `w_ml ∈ {0.7, 0.8, 0.9}`. Chosen for
interpretability — one formula, one sentence, reproducible in a defense.
Brute-force weight search was avoided deliberately: it optimises the
metric rather than producing a defensible design.

### 6.1 Result worth stating plainly

**Fusion did not beat ML alone.** See `phase2b-evaluation.md` §5 for the
ablation table and the analysis of why. This is reported as measured; the
brief explicitly forbids forcing combined fusion to win.

---

## 7. Threshold selection

Default 0.5 is not assumed. The operating threshold is chosen on the
**validation fold only**:

> Take the **highest** threshold that still achieves recall ≥ 0.90.

Rationale: for this product a missed phishing URL is the costlier error,
so recall is a **constraint** and precision is what gets maximised within
it. The same threshold policy is used for every model, so comparisons are
like-for-like.

The selected threshold is persisted in the model metadata and used at
inference. It is never tuned on the test set.

---

## 8. Calibration

Two methods, both fitted on **validation** only:

- **Platt scaling** — logistic regression on the logit of the raw score
- **Isotonic regression** — monotone step-free mapping

Measured by Brier score and reported per model per split in
`results/phase2b/calibration_results.csv`.

---

## 9. Feature importance

Three sources, because each has a different failure mode:

| Source | Use | Caveat |
|---|---|---|
| Logistic coefficients | Direction and marginal effect | Correlated features share weight |
| Tree importance | Total gain across splits | Prefers high-cardinality features |
| Permutation importance | Empirical drop when shuffled | Computed on a validation sample for tractability |

Importance is **not** causal. A feature can rank highly because it
correlates with a true cause without being one. See
`phase2b-evaluation.md` §7.

---

## 10. Reproducibility

| Element | Value |
|---|---|
| Seed | `random_state = 42` |
| Python | recorded in `results/phase2b/environment.json` |
| Package versions | recorded in the same file |
| Dataset checksums | SHA-256 in `datasets/manifests/` |
| Timestamp | recorded in model metadata |

Run the full experiment with:

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.\.venv\Scripts\python.exe -m scripts.run_phase2b_experiment
```

---

## 11. Methodology limitations

Stated here so they are not discovered later:

1. **Single training corpus.** All conclusions are PhiUSIIL-specific
   until the cross-dataset experiment is read alongside them.
2. **URL-string only.** Content-based signals are invisible, which is a
   large share of what makes a page phishing.
3. **Static snapshot.** Domains change hands; the corpus has an age.
4. **No temporal split.** A random split cannot measure performance
   drift on newly-registered domains.
5. **Rule weights are hand-set.** Phase 2B measures their empirical
   behaviour but does not re-derive them.
