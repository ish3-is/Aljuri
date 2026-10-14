# Phase 2E — HTTPS Bias

> The central experiment of the final URL phase.

---

## 1. The question

Can the HTTPS distribution problem — which forced `uses_https` and
`uses_http` out of the model in Phase 2B — be corrected by adding a
legitimate corpus with realistic HTTPS prevalence?

---

## 2. Measured association per corpus

| Corpus | P(HTTPS \| legitimate) | P(HTTPS \| phishing) | Lift |
|---|---|---|---|
| MUD 2026 | 0.9209 | 0.8196 | 0.89 |
| PhishTank | 0.0000 | 0.9116 | — (no legit. class) |
| PhiUSIIL | 1.0000 | 0.4863 | **0.49** |
| Realistic (2D) | 0.0497 | 0.2944 | **5.93** |

**The sign of the association differs between corpora.** PhiUSIIL and MUD
associate HTTPS with *legitimate*; the Phase 2D corpus associates it with
*phishing*, by a factor of nearly six.

A single model trained across them faces a direct contradiction and must
resolve it arbitrarily.

---

## 3. Why the feature was excluded, restated

This is not "HTTPS is useless for phishing". It is:

> **In these corpora, HTTPS measures crawl methodology, not attacks.**

PhiUSIIL's legitimate URLs are 100% HTTPS because of how they were
collected. The Phase 2D corpus is 4.97% HTTPS for the same reason. The
feature encodes collection provenance.

Corroborating evidence: a classifier told only the scheme columns can
distinguish the new legitimate corpus from the existing ones — corpus
accuracy rises **0.8283 → 0.9278** when scheme features are added. The
corpus is identifiable *by scheme alone*.

---

## 4. Did the new source help?

The new corpus is **99.99% HTTPS** on its legitimate side. It agrees with
PhiUSIIL and MUD rather than reversing them, so on consistency grounds it
should have helped.

It did not.

| Candidate | Real-world FP | Phishing FN | Recall @FPR 0.05 | Worst-corpus AUC |
|---|---|---|---|---|
| v3 (Phase 2D) | **5/14** | **0** | **0.750** | 0.8481 |
| Phase 2E candidate | 6/14 | 1 | 0.701 | **0.8538** |

One marginal gain, four regressions.

**The reason is domain overlap.** 95.3% of the new corpus's domains
already appear in MUD and 95.9% in the Phase 2D corpus. Adding it
enriches the scheme distribution but adds almost no new legitimate
*structure*, while diluting the phishing class. The model became slightly
better at ranking held-out corpora and slightly worse at the task that
matters.

---

## 5. Decision

**`uses_https` and `uses_http` remain excluded from model input.**

Two independent reasons, recorded separately because either alone would
be sufficient:

1. **Empirical.** The gain from re-enabling them (+0.029 worst-corpus
   AUC) is within noise, and doing so measurably worsens source
   separability.
2. **Architectural.** The serving contract slices to 39 columns;
   `assert_schema_matches` would refuse a scheme-aware model at load
   time. Changing that is a deliberate engineering decision, not a
   side-effect of a promotion gate.

---

## 6. What would actually fix it

A legitimate corpus that is simultaneously **HTTPS-diverse** (not
99.99% one scheme), **path-diverse**, and **domain-new**. No such corpus
was available: the preferred UNB CIC-URL-2016 is now gated behind a
request form, and the Common Crawl index proved unviable at scale.

The honest conclusion is that this defect is **not fixable with the data
currently obtainable**, and the workaround (exclude the features) remains
the correct engineering response.