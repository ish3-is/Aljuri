# Phase 2D — Methodology

> Feeds **Chapter 5 — Methodology**.

---

## 1. Design

Phase 2D changes one thing: the **negative-class distribution**. The
model, feature extractor, splitting strategy and evaluation protocol are
held constant so the effect is attributable.

| Component | Choice | Rationale |
|---|---|---|
| Extractor | BASIRAH production extractor v2.1.0 | Unchanged; no separate extractor |
| Features | 39 (scheme features excluded) | Per the Phase 2B inversion finding |
| Models | LogisticRegression, RandomForest, HistGradientBoosting, XGBoost | Same four as Phase 2C |
| Split | Grouped by registered domain | Leakage assertion retained |
| Threshold | Tuned on validation, persisted | Phase 2C bug fix reused |

---

## 2. Corpus acquisition

Four sources acquired, three rejected. Full detail in
`phase2d-corpus-acquisition.md`.

| Source | Role | Licence |
|---|---|---|
| HF `ealvaradob/phishing-dataset` (URL subset) | realistic legitimate + phishing | Apache-2.0 |
| PhishTank online-valid | held-out phishing | PhishTank ToU |
| Tranco top-1m | domain-diversity reference only | research |

**Rejected:** LegitPhish (its legitimate class is 98.4% bare domains —
training on it would have reinforced the defect), Common Crawl index
(not viable at scale), phreshphish (too large; each row carries page
HTML).

The source search was delegated. Its reported "99.9% path-bearing" figure
proved **circular** — measured from a pre-filtered extract — and the
correct 87.58% was measured from the raw source.

---

## 3. Label discipline

Carried forward from the Phase 2B defect:

- `LabelSemantics` declares each corpus's encoding explicitly.
- `LabelOrientationError` refuses unstated numeric orientations.
- PhishTank rows are **all phishing** by source definition — human
  verified, the highest-confidence label source in the project.

**PhishTank is used as a held-out phishing set**, never trained on, so
phishing recall is measured on data the model has never seen.

---

## 4. Corpus quality gate

The Phase 2C gate was extended with six checks for a legitimate corpus:

| ID | Check | Severity |
|---|---|---|
| C13 | Realistic path representation | blocking |
| C14 | Query-string representation | blocking |
| C15 | Domain diversity | blocking |
| C16 | Deep-path representation | blocking |
| C17 | Source concentration | blocking |
| C18 | Suspicious shortcut risk | blocking |

These exist because a legitimate corpus of bare domains is the exact
defect Phase 2D corrects, and nothing else in the pipeline would detect
it.

The new checks correctly flagged the project's own **test fixtures** as
unrealistic. The fixtures were corrected rather than the checks
weakened.

---

## 5. Evaluation

Four levels, because in-domain accuracy proved uninformative in Phase
2B:

1. **Grouped-domain AUC** — leakage-free in-domain
2. **Worst-corpus AUC** — cross-corpus robustness
3. **Held-out PhishTank recall** — phishing detection on unseen data
4. **Real-world semantic regression** — the operational criterion

---

## 6. The fairness correction

This is the most important methodological decision in Phase 2D.

The first analysis compared models on **raw recall** and concluded the
candidate had regressed. That comparison is invalid: recall depends on
the operating threshold, and the two models were evaluated at
*different* false-positive rates.

| Model | Recall | at FPR |
|---|---|---|
| v1 | 0.9788 | **0.658** |
| v3 candidate | 0.9092 | 0.137 |

v1 achieves its recall by flagging two-thirds of legitimate traffic. Any
comparison at those operating points measures aggressiveness, not
detection ability.

**Policy adopted:** models are compared at a **matched false-positive
rate**. At FPR 0.05, v1 detects 0.260 and the candidate 0.760.

This reversed the promotion decision, and it was the right call.

---

## 7. Promotion policy

Six criteria, all of which must hold:

1. Real-world FP improvement ≥ 5 cases
2. Phishing recall does not regress **at matched FPR**
3. Grouped performance remains strong
4. Cross-corpus robustness remains strong
5. Calibration acceptable
6. Model behaviour explainable

Criteria 1, 3, 4 and 6 pass. Criterion 2 passes only under the matched-
FPR comparison, which is why §6 precedes it.

**v1 was not overwritten.** The candidate is staged as
`basirah-url-v3.joblib`; swapping production is a separate reviewed act.

---

## 8. Reproducibility

`random_state = 42`; environment, checksums and run metadata in
`results/phase2d/environment.json` and
`datasets/manifests/phase2d_legitimate_sources.json`.

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.\.venv\Scripts\python.exe -m scripts.run_phase2d_experiment
.\.venv\Scripts\python.exe -m scripts.phase2d_artifacts
.\.venv\Scripts\python.exe -m scripts.phase2d_artifacts2
```