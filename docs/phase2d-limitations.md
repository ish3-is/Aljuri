# Phase 2D — Limitations

> Feeds **Chapter 8 — Security, Privacy and Limitations**.

---

## 1. The primary success criterion was not fully met

| | |
|---|---|
| Target in the brief | ≤4/14 real-world false positives (reduction of 6) |
| Achieved | **5/14** (reduction of 5) |

The improvement cleared the implemented materiality floor but missed the
brief's stated numeric target. Ten URLs improved; four remain false
positives.

This phase reduced the problem substantially. It did not solve it.

---

## 2. Remaining false positives are structural

| Category | Flagged | Rate |
|---|---|---|
| qanda | 1/1 | 100% |
| news | 1/1 | 100% |
| documentation | 2/3 | 67% |
| university | 2/3 | 67% |
| repository | 2/4 | 50% |

University portals and documentation paths frequently contain
credential-like vocabulary (`/student/registration`,
`/account/restore`). On URL strings alone these genuinely overlap with
phishing structure. No amount of additional legitimate training data
will separate them reliably — the distinguishing evidence is page
content, which this project deliberately does not fetch.

---

## 3. The new corpus does not fix HTTPS skew

The Phase 2D corpus is **6.58% HTTPS**, far below real-world usage
(~95%+).

| Corpus (legitimate) | % HTTPS |
|---|---|
| PhiUSIIL | low |
| Phase 2D corpus | **6.58** |

Since HTTPS is far more prevalent among phishing URLs in every corpus,
this can reinforce the scheme inversion Phase 2B identified. Scheme
features remain excluded from model input for that reason — the
exclusion is a workaround for a data problem the new corpus inherits
rather than solves.

---

## 4. Source separability increased

| Corpus count | Source-classifier AUC |
|---|---|
| 2 corpora (Phase 2C) | 0.9916 |
| **4 corpora (Phase 2D)** | **0.9477** (ovr macro) |

Adding the realistic corpus did **not** make sources harder to
distinguish; if anything it made the new corpus more identifiable
relative to the others. A phishing score remains partly a corpus
fingerprint.

---

## 5. Corpus provenance is weaker than the phishing side

| Source | Label confidence |
|---|---|
| PhishTank | **Human-verified** contributors |
| HF corpus legitimate | **Upstream-curated, unverified** |

No individual legitimate URL was independently verified, and none could
be without visiting it — which this project does not do. The asymmetry
is material: a false legitimate label teaches the model to miss phishing.

Both Phase 2D sources descend from PhishTank/Alexa-era crawls, so they
are **not fully independent** of PhiUSIIL. Measured domain overlap is
9.1% and 8.0%, so most domains are new, but lineage is shared.

A genuinely independent modern source (`phreshphish`, 2025-26 crawl)
was identified but proved unusable at bulk scale — ~30 GB for ~1,345
extractable URLs.

---

## 6. Temporal skew

The legitimate corpora are dominated by 2011–2015 era crawls. Many of
those URLs are likely dead. This does not affect URL-string analysis
(the strings are still valid training material) but means the corpus
does not reflect modern URL structure.

---

## 7. Statistical

| Limitation | Detail |
|---|---|
| Single seed | `random_state = 42`; no variance estimate |
| Semantic set is 34 hand-built URLs | Not a statistical sample; 1 case = 2.9% |
| No hyperparameter search | Defaults, for tractability |
| Threshold 0.4918 vs v1's 0.9965 | Different operating points by design |
| Calibration not re-evaluated | Phase 2B found it unhelpful; recorded as "not applied" rather than measured again |

---

## 8. Adversarial

No adversarial testing. An attacker aware that deep documentation paths
now score low could exploit it, though the phishing side (0.74–0.92 at
every depth) limits the available room.

---

## 9. Ethical

| Consideration | Position |
|---|---|
| Privacy | URL strings analysed locally; no request made to them |
| Retention | None; API stateless |
| False positives | Reduced but **unresolved** (5/14) |
| Bias | Inherits three corpora's profile and their collection artefacts |
| Licensing | Apache-2.0, CC BY 4.0, PhishTank ToU — all permit research use with attribution |

The false-positive burden is reduced but not removed. A detector that
still flags a third of well-known legitimate URLs will still cause harm
if used for automated blocking. **v3 should not be used for automated
blocking** on this evidence.

---

## 10. What would most improve this

1. **Swap v3 into production** — it dominates v1 on every metric
   measured, at matched FPR.
2. **A legitimate corpus with realistic HTTPS** — fixes §3, the one
   defect the new corpus carries.
3. **A third-party review of the false negatives** — PhishTank recall is
   0.909, so ~9% of verified phishing is missed.
4. **Page-content signals** for university/documentation overlap — the
   only way to separate §2, and the project's main scope limitation.
5. **An independent modern legitimate corpus** to address §5/§6.