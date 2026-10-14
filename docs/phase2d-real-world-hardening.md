# Phase 2D — Real-World Hardening

> **Research question:** Can augmenting the training distribution with
> realistic legitimate URLs reduce phishing false positives without
> materially degrading phishing detection?
>
> **Answer: yes.** Real-world false positives halved, and phishing
> detection *improved* once compared fairly.

---

## 1. The problem being solved

Phase 2B/C established that the trained model accused ordinary
websites of phishing:

| URL | v1 score |
|---|---|
| `docs.python.org/3/library/asyncio.html` | 1.000 |
| `github.com/anthropics` | 1.000 |
| `developer.mozilla.org/en-US/docs/Web` | 1.000 |

**10 of 14** well-known legitimate URLs were flagged.

The cause was measured, not assumed: **0 of 134,850** legitimate
PhiUSIIL URLs carry a path. The model learned *"has a path ⇒ phishing"*.

---

## 2. The intervention

Add a legitimate corpus whose structure resembles the modern web.

| | PhiUSIIL legitimate | Phase 2D corpus |
|---|---|---|
| % with a path | **0.00%** | **87.58%** |
| Rows | 134,850 | 444,916 |
| Distinct domains | 175,508 | 111,805 |

The new corpus is **91% domain-disjoint** from PhiUSIIL (5,552 of 60,802
shared), so it expands coverage rather than duplicating it.

Full provenance, including three failed sources and one actively harmful
rejection, is in `phase2d-corpus-acquisition.md`.

---

## 3. Result

### 3.1 Headline

| Metric | v1 | v3 candidate | |
|---|---|---|---|
| Real-world legitimate FP | 10/14 | **5/14** | ✅ halved |
| **Recall @ matched FPR 0.05** | 0.2601 | **0.7601** | ✅ **+0.50** |
| Worst-corpus ROC-AUC | 0.3112 | **0.8481** | ✅ +0.54 |
| Grouped-domain ROC-AUC | 0.5738 | **0.9476** | ✅ +0.37 |
| Semantic phishing false negatives | — | **0** | ✅ |

### 3.2 The comparison that changed the decision

The first analysis compared **raw recall** and concluded the candidate
was worse:

> v1 = 0.9788, candidate = 0.9092 → "recall regressed, retain v1"

That comparison is confounded. v1 earns its recall at a **false-positive
rate of 0.658** — it flags two-thirds of all legitimate traffic. Recall
measured at *different operating points* does not measure detection
quality; it measures how aggressively a model accuses.

At a matched 5% false-positive rate:

| Model | Recall |
|---|---|
| v1 | 0.2601 |
| v3 candidate | **0.7601** |

The candidate detects **nearly three times** as much phishing at an
acceptable false-alarm rate. The gain was **not** bought with missed
attacks, which is what the raw comparison suggested.

---

## 4. Path bias is eliminated

This was the phase's central question, measured directly in
`path_bias_analysis.csv`.

Mean predicted phishing probability by path depth:

| Depth | Legitimate | Phishing | Separation |
|---|---|---|---|
| 0 | 0.083 | 0.924 | 0.841 |
| 1 | **0.252** | 0.785 | 0.533 |
| 2 | 0.225 | 0.780 | 0.555 |
| 3 | 0.188 | 0.748 | 0.560 |
| 6 | 0.385 | 0.840 | 0.455 |

Under v1, legitimate depth-1 URLs scored **~1.000**. Under v3 they score
**0.252**, while phishing remains 0.74–0.92 at *every* depth.

The model no longer infers phishing from structural complexity. Its
top features are now phishing-specific rather than structural:

| Feature | Group | Importance |
|---|---|---|
| `suspicious_tld` | lexical | 0.326 |
| `is_excessive_hyphen` | derived flag | 0.245 |
| `subdomain_depth` | structure | 0.039 |
| `is_ip_host` | identity | 0.035 |

---

## 5. Where it still fails

Category-level false positives (`category_fpr.csv`):

| Category | Flagged | Rate |
|---|---|---|
| qanda | 1/1 | 100% |
| news | 1/1 | 100% |
| documentation | 2/3 | 67% |
| university | 2/3 | 67% |
| repository | 2/4 | 50% |

**Clean** (no false positives): encyclopedia, academic, search, media,
education, corporate, government, legacy.

Deep documentation and university paths remain the weak spot — the same
structures that carry credential-like vocabulary (`/account/restore`,
`/student/registration`) overlap genuinely with phishing patterns. The
model cannot separate them on URL strings alone.

---

## 6. Status: staged, not shipped

The candidate is written to `models/basirah-url-v3.joblib` with metadata
stating it *"remains unreviewed"*.

**`basirah-url-v1.joblib` is byte-identical and verified unmodified:**

| | |
|---|---|
| SHA-256 | `db682cf8f472127961d4ad4a6062ea8210b413469f014aa51e5618802a07a802` |
| Matches its recorded metadata | yes |
| Still loads and reproduces 10/14 | yes |

Swapping production is a separate, deliberate act.

---

## 7. Honest accounting

| | |
|---|---|
| FP target in the brief | ≤4/14 (reduction of 6) |
| Achieved | **5/14** (reduction of 5) |

The improvement met the implemented materiality floor of 5 cases but
**missed the brief's stated numeric target of ≤4/14**. Reporting 5/14 as
"halved" is accurate; calling it "target met" would not be.

---

## 8. Known remaining defect

The new corpus is **6.58% HTTPS**, far below real-world usage. It does
not fix the scheme skew, and the four-corpus source-classifier AUC rose
to **0.9477** — the new corpus is *more* distinguishable from the
existing corpora, not less. See `phase2d-limitations.md`.