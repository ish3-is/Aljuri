# Phase 2C — Limitations

> Feeds **Chapter 8 — Security, Privacy and Limitations**.

---

## 1. The false-positive problem is unsolved

This is the dominant limitation and the reason v2 was not promoted.

| | v1 | Multi-corpus candidate |
|---|---|---|
| Real legitimate URLs flagged | 10 / 14 (71%) | 9 / 14 (64%) |
| Semantic legitimate cases flagged | 23 / 23 (100%) | 18 / 23 (78%) |

**Phase 2C did not solve this.** Cross-corpus generalization improved
dramatically; real-world false positives barely moved.

The cause is structural, not a modelling failure: **both corpora treat a
path-bearing URL as suspicious**, so neither contains the population
BASIRAH needs. Real legitimate URLs overwhelmingly have paths
(`docs.python.org/3/library/asyncio.html`).

No amount of additional training on these two corpora will fix it. A
corpus of realistic legitimate URLs is required.

---

## 2. Two corpora are not "multi-corpus"

With n=2, "generalizes across corpora" rests on a single comparison. A
finding that could equally be phrased: *PhiUSIIL and MUD disagree*.

A third corpus — ideally from a different collection method, language
and time period — would establish that the result is a property of
corpus diversity rather than of this particular pair.

---

## 3. The corpora are not independent enough

The corpus-classification diagnostic reports AUC **0.9916** for telling
the two corpora apart. They encode different collection methodologies,
which means:

- the generalization gap may partly reflect *collection* differences
  rather than genuine population differences;
- the low URL overlap (57 URLs, 8,129 shared domains) does not
  guarantee independence.

This caveat applies to every cross-corpus number in Phase 2C, including
the 0.9863.

---

## 4. Heuristics remain low-coverage

| Configuration | F1 | Recall | ROC-AUC |
|---|---|---|---|
| heuristics only | 0.0947 | 0.0504 | 0.5483 |
| ML only | **0.8525** | 0.8792 | **0.9380** |
| ML + heuristics @90% | 0.8448 | 0.8461 | 0.9385 |
| ML + heuristics @80% | 0.8296 | 0.7996 | 0.9382 |
| ML + heuristics @70% | 0.7994 | 0.7229 | 0.9366 |

**Fusion does not improve on ML alone.** Heuristics reach recall 0.05 —
they see 5% of phishing URLs.

They are retained as an **explainability and evidence layer**, not a
scoring component. This is a deliberate decision: their rules are
transparent and auditable, and they do not depend on corpus-specific
statistics.

---

## 5. Feature selection could not be validated as a general strategy

`stable_only` (3 features) collapses to near-chance. That falsifies H4
in this setting, but it does not establish that feature-stability
filtering is wrong in general — with only 3 stable features, the result
may reflect insufficient signal rather than the principle.

---

## 6. URL-string only

Unchanged from Phase 2A and still the largest structural limit:

| Invisible signal | Consequence |
|---|---|
| Page content | Most branding-similarity evidence |
| Redirect chains | A benign URL redirecting to phishing scores benign |
| **Domain age** | The single strongest available phishing indicator |
| Certificate state | No issuer, age or mismatch signal |
| WHOIS / hosting | Absent |

Domain age would address §1 directly: a legitimate documentation URL is
on an old, stable domain, while phishing domains are typically new. No
feature in the current set captures this.

---

## 7. Statistical and methodological

| Limitation | Detail |
|---|---|
| Single seed | `random_state=42`; no variance estimate |
| No hyperparameter search | Defaults, for tractability |
| Group split is unstratified | Domain assignment is random, so class balance is measured rather than guaranteed (achieved 0.506 / 0.474) |
| Semantic suite is hand-built | 34 cases; not a statistical sample |
| LOCO removes domains, not rows | Slightly stricter than a standard holdout |
| MUD class exclusion | Defacement and malware are excluded; a different task definition might include them |

---

## 8. Adversarial considerations

No adversarial robustness testing. An attacker aware of the 39 features
could craft URLs matching the phishing-side feature profile. Multi-corpus
training does not change this — it makes the learned profile broader,
which may make evasion *easier*, not harder.

---

## 9. Privacy and ethical considerations

| Consideration | Position |
|---|---|
| Data submitted | A URL string, analysed locally; no request is made to it |
| Retention | None; the API is stateless |
| Third parties | None called |
| Datasets | Public research corpora under their licences (CC BY 4.0, CC BY-NC-SA 4.0) |
| **False positives** | **Severe and unresolved** — see §1 |
| Bias | The model reflects both corpora's profile of "phishing" and their collection artefacts |

The false-positive burden deserves emphasis. A tool that flags
`docs.python.org` and `developer.mozilla.org` trains users to ignore it
immediately, and the cost falls on the legitimate sites being defended.

---

## 10. Honest summary

**What Phase 2C established**

- Single-corpus URL phishing models transfer **negatively** (7 of 8
  models score below chance; the eighth reaches only 0.60).
- Multi-corpus training fixes this (0.18–0.60 → 0.94–0.99) **without**
  sacrificing in-domain accuracy.
- The mechanism is feature-level inversion plus corpus-identifiable
  features (corpus-classifier AUC 0.9916).
- Restricting to stable features is counter-productive.

**What it did not establish**

- Any usable false-positive rate on real-world URLs.
- That the result generalizes beyond this pair of corpora.
- That a production model was produced. **v1 remains in production.**

---

## 11. Recommendation

The corpus-quality gate (`app/ml/corpus_quality.py`) is the most
transferable artefact of this phase. It should be run against any future
URL phishing corpus before training.

Priority order:

1. **Obtain a legitimate-URL corpus with realistic path structure.** The
   single blocker for §1.
2. **Add domain-age features** — the strongest available phishing
   signal, and independent of path structure.
3. **Third corpus** for independent validation.
4. **Character n-grams** for sub-token pattern matching.