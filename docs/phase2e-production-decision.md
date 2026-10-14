# Phase 2E — Production Decision

> The final URL-intelligence decision.

---

## 1. Decision

## **PROMOTE basirah-url-v3**

`models/ACTIVE_MODEL.json` now serves `basirah-url-v3.joblib`, superseding
`basirah-url-v1.joblib`.

**Rollback** is a one-line edit to that file — no code change required.
v1 is retained on disk with its SHA-256 recorded, and remains loadable by
name.

---

## 2. Why not v4

The Phase 2E candidate was trained on the new HTTPS-realistic corpus and
**failed three of its acceptance gates**:

| Gate | v3 | Candidate | |
|---|---|---|---|
| Real-world FP not worse | **5/14** | 6/14 | ❌ |
| Phishing FN zero | **0** | 1 | ❌ |
| Matched-FPR recall not worse | **0.750** | 0.701 @0.05 | ❌ |

It improved worst-corpus AUC (0.8538 vs 0.8481) and grouped AUC (0.9504
vs 0.9476) — both marginal — against four regressions that matter
operationally.

`basirah-url-v4.joblib` is retained as a **research artifact, not
promoted**.

---

## 3. Why v3 over v1

| Metric | v1 | v3 | |
|---|---|---|---|
| Real-world legitimate FP | 10/14 | **5/14** | ✅ halved |
| Semantic phishing FN | 11/11 | **0/11** | ✅ all caught |
| Recall @FPR 0.01 | 0.155 | **0.558** | ✅ |
| Recall @FPR 0.05 | 0.289 | **0.750** | ✅ |
| Worst-corpus AUC | 0.311 | **0.848** | ✅ |
| Grouped AUC | 0.574 | **0.948** | ✅ |

v3 leads on **every** fair measure. The promotion is not marginal.

---

## 4. The safety disclosure

**v3 is not cleared for automated blocking.** This is served by the API:

```json
{
  "fit_for_automated_blocking": false,
  "notice": "This model is advisory only. It is not validated for
             automated blocking or takedown: on a curated set of 14
             well-known legitimate URLs it misclassifies 5, and on
             held-out verified phishing it misses roughly a quarter at
             a 5% false-positive rate. Treat a verdict as evidence to
             review, not a decision to enforce."
}
```

Shipping v3 without this disclosure would present a detector that
accuses `docs.python.org`, `github.com/anthropics` and
`stackoverflow.com` as implying those sites are malicious. A tool that
does that without warning trains users to ignore it.

---

## 5. What remains false positives

5 of 14 well-known legitimate URLs are still misclassified:

- `docs.python.org/3/library/asyncio.html`
- `github.com/anthropics`
- `gitlab.com/group/subgroup/project`
- `stackoverflow.com/questions/1`
- `www.youtube.com/watch?v=x`

All five carry a path. The model learned from corpora in which a
legitimate URL rarely had one. Documentation and repository URLs overlap
structurally with credential-harvesting URLs, and on URL strings alone
that overlap is genuine.

---

## 6. What this closes

URL intelligence is **not** declared production-ready. It is production
*deployed*, advisory, and honestly labelled. Per the brief there is no
Phase 2F: the remaining defects are data defects, and more model work on
the available corpora has now been demonstrated twice not to fix them.

The work moves to **Phase 3 — Synthetic Media Intelligence**.