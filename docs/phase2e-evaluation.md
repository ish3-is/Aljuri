# Phase 2E — Evaluation

> Feeds **Chapter 7 — Results**. All figures from
> `backend/results/phase2e/`.

---

## 1. Source

| Property | Value |
|---|---|
| Name | Mendeley Data "Phishing URL dataset" (legitimate subset) |
| Licence | CC BY 4.0 |
| Rows / usable | 345,738 / **345,738** |
| % HTTPS | 99.99 |
| % with path | 85.04 |
| % with query | 13.29 |
| Registered domains | 84,682 |
| Domain overlap with MUD / realistic | **95.3% / 95.9%** |
| Per-domain cap selected | **100** |

---

## 2. Cap comparison

| Cap | Rows | Grouped AUC | Worst-corpus | PT recall @0.05 |
|---|---|---|---|---|
| 25 | 179,417 | 0.9472 | 0.8431 | 0.6871 |
| 50 | 198,627 | 0.9479 | 0.8463 | 0.6815 |
| **100** | **218,285** | **0.9504** | **0.8483** | **0.7007** |

Selected on generalization; row count excluded from the ranking.

---

## 3. Matched-FPR recall — the decisive comparison

| Model | @0.01 | @0.03 | @0.05 | @0.10 |
|---|---|---|---|---|
| v1 (previous production) | 0.155 | 0.155 | 0.289 | 0.344 |
| **v3 (promoted)** | **0.558** | **0.698** | **0.750** | **0.842** |
| Phase 2E candidate | 0.507 | 0.635 | 0.701 | 0.791 |

v3 leads at every operating point. The Phase 2E candidate never catches it.

---

## 4. Candidate vs v3

| Metric | v3 | Candidate | |
|---|---|---|---|
| Real-world FP (of 14) | **5/14** | 6/14 | ❌ |
| Semantic phishing FN | **0** | 1 | ❌ |
| Recall @FPR 0.05 | **0.750** | 0.701 | ❌ |
| Worst-corpus AUC | 0.8481 | **0.8538** | ✅ only gain |
| Grouped AUC | 0.9476 | **0.9504** | ✅ |

Three gates failed. One marginal improvement against four regressions.

---

## 5. Path bias — regression check

| | Value |
|---|---|
| Legitimate depth-0 mean probability | 0.0932 |
| Phase 2D value for comparison | 0.0826 |
| Drift | +0.011 (threshold 0.05) |
| Phishing depth-0 | 0.9089 |
| **Verdict** | **No regression** |

The Phase 2D fix survives the new corpus.

---

## 6. Heuristic fusion

| Arm | Recall | FPR |
|---|---|---|
| Heuristics only | 0.431 | 0.425 |
| ML only | **0.900** | **0.171** |
| OR-fused | 0.940 | 0.534 |

Fusion buys 4 points of recall for 36 points of false-positive rate.
**Rejected.** The heuristic engine remains an evidence and explanation
layer, not a scoring component.

---

## 7. Calibration

Isotonic won on Brier by 0.00054, below the 0.002 margin required to
distinguish a real improvement from noise. **Not applied.** Raw
probabilities are served.

---

## 8. Corpus-source classifier

Adding scheme columns raises corpus-classifier accuracy **0.8283 →
0.9278**. The new legitimate corpus is identifiable by scheme alone,
which is independent evidence for keeping scheme features excluded.

---

## 9. Leakage assertions

| Assertion | Result |
|---|---|
| Original 14 URLs in training | excluded |
| Expanded-holdout domains in training | excluded |
| PhishTank domains in training | excluded |
| train ∩ test domains | **empty** |