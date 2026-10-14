# Model Card — BASIRAH URL v3

**Status: PRODUCTION (advisory) · Promoted 2026-10-04 · Phase 2E**
**Not cleared for automated blocking.**

---

## 1. Summary

| | |
|---|---|
| Model | `basirah-url-v3.joblib` |
| Algorithm | XGBoost, all features, 400 trees, depth 8, `tree_method=hist` |
| Inputs | 39 URL-derived features from 41 computed |
| Extractor | `FEATURE_EXTRACTOR_VERSION = 2.1.0` |
| Threshold | **0.4918** |
| Supersedes | `basirah-url-v1` (retained, rollback available) |
| Rejected sibling | `basirah-url-v4` (Phase 2E candidate, not promoted) |

---

## 2. Intended use

Triage and **evidence gathering**. A human reviews a verdict before any
action.

### Out of scope

- Automated blocking, takedown, or quarantine
- Enterprise allow/block list generation
- Any enforcement without human review

The API states this: `fit_for_automated_blocking: false`.

---

## 3. Training data

| Corpus | Rows | Role |
|---|---|---|
| PhiUSIIL | 235,362 | training |
| MUD 2026 (benign + phishing) | 513,574 | training |
| Realistic (HuggingFace `ealvaradob/phishing-dataset`) | 813,603 | training |
| PhishTank online-valid | 74,989 | **held out — never trained on** |

Malware and defacement classes were excluded from MUD throughout.

---

## 4. Performance

**Grouped-domain split** (registered domains disjoint between train and
test):

| Metric | Value |
|---|---|
| ROC-AUC | **0.9476** |
| Real-world legitimate FP | **5/14** |
| Semantic phishing FN | **0/11** |

**Held-out phishing (PhishTank)** — recall at matched false-positive rate:

| FPR | Recall |
|---|---|
| 0.01 | 0.558 |
| 0.03 | 0.698 |
| 0.05 | 0.750 |
| 0.10 | 0.842 |

**Cross-corpus**: worst-corpus ROC-AUC **0.8481** (PhiUSIIL → MUD
transfer is the hard case; single-corpus models fall below chance).

---

## 5. Known failure modes

| Failure | Measured |
|---|---|
| Legitimate URL with a path misclassified | 5/14 in the real-world set |
| Verified phishing missed | ~25% at FPR 0.05 |
| Credential-harvesting URL vs. legitimate login | indistinguishable on URL strings alone |

The five known false positives are all path-bearing:
`docs.python.org/3/library/asyncio.html`, `github.com/anthropics`,
`gitlab.com/group/subgroup/project`, `stackoverflow.com/questions/1`,
`www.youtube.com/watch?v=x`.

---

## 6. Excluded features

`uses_https` and `uses_http` are **computed and displayed but not model
inputs**.

Across corpora their class association changes sign (lift 0.49 on
PhiUSIIL, 0.89 on MUD, 5.93 on the realistic corpus). They encode crawl
methodology, not attacks. Re-enabling them was tested in Phase 2E and
rejected on both empirical and architectural grounds.

---

## 7. Ethics and limitations

- URL-string inference only. No page content, no reputation, no WHOIS.
- Corpus-source classification remains highly accurate (0.9477), so part
  of any score is a corpus fingerprint.
- The honest failure direction is **false accusation of legitimate
  sites**, not missed phishing. This is why the advisory label is not
  optional.
- Evidence of false positives is presented alongside recall in the UI and
  API, not hidden behind a single verdict.

---

## 8. Reproducibility

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.\.venv\Scripts\python.exe -m scripts.run_phase2d_experiment
```

Decision record: `backend/results/phase2d/promotion.json`.
Phase 2E promotion: `backend/results/phase2e/promotion_decision.json`.
Active model: `backend/models/ACTIVE_MODEL.json`.