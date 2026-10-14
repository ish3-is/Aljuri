# Phase 2E — Limitations

> Feeds **Chapter 9 — Limitations and Future Work**.

---

## 1. What Phase 2E did not achieve

The phase set out to correct the HTTPS and source-distribution problem
without losing Phase 2D's gains. **It did neither.**

The new legitimate corpus is 99.99% HTTPS and 84,682 domains — but 95.3%
of those domains already appear in MUD and 95.9% in the Phase 2D corpus.
It added scheme realism without adding legitimate structure, and the
resulting model regressed on real-world false positives, phishing false
negatives, and recall at all four matched FPRs.

The Phase 2B exclusion of `uses_https` and `uses_http` therefore stands,
and no new evidence contradicts it.

---

## 2. Residual limitations of the promoted model

| # | Limitation | Evidence |
|---|---|---|
| 1 | **5 of 14** well-known legitimate URLs misclassified | `semantic_regression_original.csv` |
| 2 | ~25% of held-out verified phishing missed at FPR 0.05 | PhishTank holdout |
| 3 | Corpus source classifier remains highly accurate | Phase 2C 0.9916 → Phase 2E 0.9477 |
| 4 | Legitimate and phishing credential paths are structurally identical on URL strings | by construction |
| 5 | No domain age, reputation, or WHOIS signal | out of scope by brief |
| 6 | Scheme distribution unrepresentative in every corpus | Phase 2E §4 |

Limitations 1 and 4 share one cause: **URL strings do not contain the
information needed to separate "login page" from "phishing login page"**.
That needs page content or reputation, not better features.

---

## 3. Methodological limitations

| # | Issue |
|---|---|
| 1 | Smoke and full runs share an output directory; a full-scale artifact set was overwritten once |
| 2 | Cap selection differed between runs (25 → 100) after the C22 sampling bug was fixed — legitimate, but it means earlier interim numbers are superseded |
| 3 | Two decision-logic errors (own-threshold recall; an invented absolute recall bar) were found and corrected during the phase |
| 4 | The expanded holdout cannot cover popular domains, which appear in every large corpus |
| 5 | The new corpus's labels are upstream-curated, not independently verified, and no URL was visited |

Item 1 is a harness defect worth fixing before any future iteration.

---

## 4. Why no Phase 2F

The brief closes the URL phase explicitly, and the evidence supports
closing it. Three separate interventions — path features, multi-corpus
training, and HTTPS-realistic augmentation — have now each been measured:

| Intervention | Result |
|---|---|
| Remove path features (2C) | Did not fix false positives |
| Multi-corpus training (2C) | Fixed transfer, not false positives |
| HTTPS-realistic corpus (2E) | Slightly worse |

The consistent finding is that the remaining defects are **corpus data
defects**, not model or feature defects. Further tuning on the available
corpora has a poor expected return, and BASIRAH is a multimodal trust
platform, not a URL-classification research project.

---

## 5. What Phase 3 should inherit

1. The `fit_for_automated_blocking: false` contract and its notice.
2. Matched-FPR evaluation as the default comparison. It is the only
   comparison that did not mislead in this project.
3. The lesson that corpus provenance, not attack structure, dominated
   every feature decision from 2B onward.

---

## 6. Recommendation

Proceed to **Phase 3 — Synthetic Media Intelligence**.

If URL work is ever revisited, it should begin with **data acquisition,
not modelling**: a genuinely domain-new, scheme-diverse, path-diverse
legitimate corpus. That corpus does not currently exist in any
publicly accessible form, which is itself a finding worth recording.