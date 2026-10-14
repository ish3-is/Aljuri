# Model Card — BASIRAH URL v1

> The model currently in production. `basirah-url-v2` was evaluated in
> Phase 2C and **not promoted**; see the promotion record in
> `results/phase2c/` and the rationale below.

---

## Model Details

| Property | Value |
|---|---|
| **Name** | BASIRAH URL v1 |
| **Technical identifier** | `basirah-url-v1` |
| **Version** | 1.0.0 |
| **Algorithm** | XGBoost (400 trees, depth 8, `tree_method=hist`) |
| **Artifact** | `backend/models/basirah-url-v1.joblib` (1.54 MB) |
| **Metadata** | `backend/models/basirah-url-v1.metadata.json` |
| **Feature extractor** | BASIRAH production extractor v2.1.0 |
| **Features** | 39 of 41 computed (`uses_https`, `uses_http` excluded) |
| **Training data** | PhiUSIIL (UCI id 967) only |
| **Corpus source** | CC BY 4.0 |

---

## Intended Use

**In scope**

- Scoring a single URL string for phishing likelihood.
- Ranking URLs by risk within one observed corpus.
- Research and academic evaluation of URL phishing classifiers.

**Out of scope**

- Any claim of production-grade accuracy on live traffic.
- Automated blocking or takedown decisions.
- Assessing page content — the model never fetches a URL.
- Any language-specific phishing detection beyond the URL string.

---

## Training Data

| Property | Value |
|---|---|
| Corpus | PhiUSIIL Phishing URL Dataset |
| Rows in file | 235,795 |
| Rows used | 235,362 |
| Class balance | 134,850 legitimate / 100,512 phishing |
| Distinct registered domains | 175,508 |
| **Label orientation** | **inverted** — `1 = legitimate`, `0 = phishing` |

### Known corpus defects

| Defect | Consequence |
|---|---|
| Label orientation inverted | Inverted model if unhandled |
| **Zero legitimate URLs have a path** | Model flags `github.com/anthropics` |
| Corpus-specific feature statistics | Poor cross-corpus transfer |

---

## Method

**Preprocessing.** BASIRAH's production URL normalizer and 41-feature
extractor. The same code serves training and inference — enforced by a
schema contract that refuses a model whose feature list or order differs.

**Training.** Stratified split 70/15/15, grouped by registered domain
(`StratifiedGroupKFold`), verified zero domain overlap.

**Threshold.** 0.9965, selected on the **validation fold only** for a
0.90 recall floor.

**Calibration.** Not applied — raw probabilities already achieved Brier
0.0023, and Platt/isotonic did not improve the selected model.

---

## Evaluation

### In-domain (grouped-domain holdout, leakage-free)

| Metric | Value |
|---|---|
| ROC-AUC | **0.9983** |
| Accuracy | 0.9541 |
| Precision | 1.0000 |
| Recall | 0.8715 |
| F1 | 0.9313 |
| FPR | 0.0000 |

### Cross-corpus (MUD 2026) — the disqualifying result

| Metric | Value |
|---|---|
| **ROC-AUC** | **0.2713** |
| F1 | 0.2734 |

**Below chance.** The model ranks MUD's benign URLs above its phishing
URLs.

### Real-world semantic behaviour

| Set | Result |
|---|---|
| Curated legitimate cases | **23 / 23 flagged (100% false positives)** |
| Well-known legitimate URLs | **10 / 14 flagged (71%)** |
| Blantant phishing | 91% caught |

---

## Known Failure Modes

| Failure mode | Cause |
|---|---|
| **Legitimate URLs with a path are flagged** | Zero legitimate PhiUSIIL rows have a path |
| Documentation and repository URLs | `docs.python.org`, `developer.mozilla.org`, `github.com/x/y` all flagged |
| Wikipedia articles with underscores | Underscore treated as suspicious |
| University portal paths | Credential-like path segments |
| **Fails entirely on other corpora** | ROC-AUC 0.271 on MUD 2026 |
| Plain-HTTP legitimate sites | Scheme distribution differs from corpus |

---

## Why v2 Was Not Promoted

Phase 2C trained a multi-corpus model reaching **0.9863** on MUD 2026 —
transforming cross-corpus generalization. It was **not promoted** because
real-world false positives improved by only **1 case** (10 → 9 of 14),
below the 5-case materiality floor.

Cross-corpus generalization is not real-world safety. Promoting on corpus
metrics alone would have shipped a model that still flags
`docs.python.org`.

---

## Ethical and Safety Considerations

| Consideration | Position |
|---|---|
| Privacy | URL string analysed locally; no request is made to it |
| Retention | None; the API is stateless |
| Third parties | None called |
| **False positives** | **Severe** — a tool that flags Mozilla documentation will be ignored, harming legitimate users |
| Bias | Inherits PhiUSIIL's profile of phishing and its collection artefacts |
| Misuse | Ranking, not blocking; output should support human judgement |

---

## Known Limitations

1. Single-corpus training; does not transfer (§ cross-corpus).
2. Corpus artifacts are baked into the learned decision boundary.
3. URL-string only — no page content, redirect, certificate or domain-age
   signal.
4. No temporal validation; cannot measure decay on new domains.
5. No adversarial robustness testing.
6. Legitimate-URL false positives remain unresolved.

---

## Ethical Use

The model's output is **probabilistic evidence, not a verdict**. It
should inform a human decision, never replace one. Given the measured
false-positive rate on ordinary legitimate URLs, automated blocking on
this model would cause real harm to legitimate sites.

Recommended disclosure to end users: *"Analysed with a model trained on
a single research dataset; accuracy on live traffic is unverified and
false positives on ordinary URLs are common."*

---

## Recommendations

1. **Do not use for automated blocking.**
2. **Do not deploy to production traffic** without a legitimate-URL
   corpus containing realistic path structure.
3. Re-run the corpus quality gate (`app/ml/corpus_quality.py`) against any
   replacement corpus — this model would be rejected by it.
4. Prefer the multi-corpus candidate for research use, with its
   limitations documented.

---

## Reproducing

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.\.venv\Scripts\python.exe -m scripts.run_phase2b_experiment   # trains v1
.\.venv\Scripts\python.exe -m scripts.run_phase2c_experiment   # evaluates v2
```

Full methodology and results: `docs/phase2b-evaluation.md`,
`docs/phase2c-results.md`, `docs/phase2c-generalization.md`.