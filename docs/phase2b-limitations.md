# Phase 2B — Limitations

> Feeds **Chapter 8 — Security, Privacy and Limitations**.
>
> These are the project's real constraints, written to be defended rather
> than minimised. **Three of them were discovered by Phase 2B itself**,
> not anticipated in advance, and are documented here in full.

---

## 1. Three corpus defects found during Phase 2B

### 1.1 Inverted label encoding (fixed)

PhiUSIIL encodes `label 1 = legitimate`, `label 0 = phishing` — the
inverse of the usual convention. The first run assumed the convention
and produced a model that scored `google.com` at 99.9% phishing.

**Why this matters beyond this project:** every metric was computed
against the same inverted labels, so the model reported AUC 0.998 while
being exactly backwards. No accuracy metric can detect this.

**Fixed by:** refusing to infer orientation from numeric data
(`LabelOrientationError`), passing it explicitly, and adding semantic
tests that assert on meaning rather than numbers.

### 1.2 PhiUSIIL's legitimate class contains zero URLs with a path

Measured from the raw corpus:

| Class | Rows | With a path |
|---|---|---|
| phishing | 100,945 | 27,451 (**27.2%**) |
| legitimate | 134,850 | **0 (0.0%)** |

"Carries a path" is therefore close to a perfect training proxy for
phishing. The model learned it correctly, and consequently flags
legitimate real-world URLs that have paths:

| URL | Score |
|---|---|
| `github.com/anthropics` | 100% phishing |
| `docs.python.org/3/library/asyncio.html` | 100% phishing |
| `developer.mozilla.org/en-US/docs/Web` | 100% phishing |

Measured over 13 well-known legitimate URLs: **9 false positives.**

On a hand-built set of real legitimate URLs:

| Variant | In-domain AUC | Legitimate flagged |
|---|---|---|
| baseline (39 features) | 0.9981 | 12/15 |
| path features removed | 0.9982 | 12/15 |

**Removing the path features does not fix it** — it preserves in-domain
accuracy and leaves the false-positive rate unchanged. The whole feature
profile encodes the artifact, not one column. The only real remedy is
multi-corpus training.

Recorded as a known defect in
`tests/test_phase2b_semantics.py::TestPhiusilPathArtifactIsAKnownDefect`
(marked `xfail` so the suite stays green while the defect is recorded).

### 1.3 Twenty of thirty-nine features are inverted across corpora

`scripts/audit_feature_directions.py` compares each feature's mean on
phishing minus its mean on benign, in both corpora:

| Result | Count |
|---|---|
| Association agrees | 19 / 39 |
| **Association OPPOSITE** | **20 / 39** |

Strongest inversions:

| Feature | PhiUSIIL | MUD 2026 |
|---|---|---|
| `url_length` | +16.69 | −14.11 |
| `path_length` | +7.58 | −20.24 |
| `registered_domain_length` | −2.11 | +2.62 |

PhiUSIIL's phishing is long, deep, hyphen-heavy brand impersonation.
MUD's phishing is short and flat. The model learned the first.

Full table: `results/phase2b/feature_direction_audit.csv`.

---

## 2. The generalization gap

| Metric | In-domain (grouped) | External |
|---|---|---|
| ROC-AUC | 0.9983 | **0.2713** |
| Accuracy | 0.9541 | 0.1591 |
| Recall | 0.8715 | 0.8872 |

**AUC 0.271 is below chance** — the model ranks MUD's benign URLs above
its phishing URLs. This follows directly from §1.3: half the feature set
points the wrong way.

Full analysis: `phase2b-generalization.md`.

---

## 3. What the model is and is not

| Claim | Supported? |
|---|---|
| Separates phishing from legitimate within PhiUSIIL | **Yes** — AUC 0.998, leakage-controlled |
| Does so without domain memorisation | **Yes** — grouped split costs ~0.4 points |
| Behaves correctly on corpus-shaped URLs | **Yes** |
| Generalises to an independent corpus | **No** — AUC 0.27 |
| Safe on real-world legitimate URLs | **No** — 9/13 false positives (§1.2) |
| Usable as a production detector | **No** |

The model is a **valid, explainable research artefact with three
measured corpus defects and a severe generalization gap.** It should be
presented as a demonstrable pipeline, not as a working detector.

---

## 4. URL-string only

BASIRAH analyses the URL and nothing else. By design (Phase 2A), it
never fetches a page. This buys safety, speed and reproducibility, and
costs a great deal of signal:

| Invisible signal | Consequence |
|---|---|
| Page content | Most branding-similarity evidence |
| Redirect chains | A benign URL that redirects to a phishing page scores benign |
| Certificate and TLS state | No issuer, age or mismatch signal |
| DNS age and registration | Newly-registered domains are a strong indicator, unavailable here |
| WHOIS / hosting reputation | Entirely absent |
| Domain age | Absent — and it would directly address §1.2 |

The domain-age signal is the most valuable missing one: it is a
well-established phishing indicator and it does not require fetching a
page.

---

## 5. Heuristic engine: strong precision, low recall

Phase 2A's 18 rules were designed a priori and hand-weighted. Phase 2B
measured them on 40,000 labelled URLs
(`results/phase2b/heuristic_rule_analysis.csv`).

**The rules are accurate but rarely fire.** This is the opposite of what
the first (inverted-label) run suggested, which reported several rules
at precision ~0 — an artifact of the label inversion, since the same
rows were mislabelled.

| Role | Count | Example rules |
|---|---|---|
| strong (precision ≥ 0.90) | **13** | `LONG_URL` 1.00, `IP_HOST` 1.00, `PUNYCODE` 1.00 |
| supporting (0.70–0.90) | 2 | `BRAND_LIKE_TOKEN` 0.86, `HIGH_ENTROPY_HOSTNAME` 0.71 |
| supporting/noisy | 3 | weighted by trigger frequency |
| rare (never fires, or near) | 5 | `ABNORMAL_PORT`, `AT_SYMBOL`, `CREDENTIAL_IN_URL` |

### 5.1 The precision/recall trade-off

| Rule | Trigger rate | Precision |
|---|---|---|
| `LONG_URL` | 4.73% | **1.000** |
| `LONG_HOSTNAME` | 4.23% | 0.992 |
| `SUSPICIOUS_TLD` | 4.15% | 0.992 |
| `HIGH_ENTROPY_URL` | 11.20% | 0.988 |
| `EXCESSIVE_HYPHENS` | 2.94% | 0.986 |
| `HIGH_ENTROPY_HOSTNAME` | 23.66% | 0.710 |

When a rule fires it is almost always right. The problem is **coverage**:
the whole set reaches only ~38% recall, so heuristics-only F1 is 0.073
with AUC 0.678.

### 5.2 What this implies

- **The rules are trustworthy.** They have no false-positive problem on
  this corpus and are defensible as transparent checks.
- **They are not a classifier.** A detector that sees only 38% of
  phishing URLs is not a detector.
- **The ML model supplies the coverage** the rules lack — which is
  exactly why the fusion arm exists, even though at a 90% ML weight the
  heuristics add nothing measurable.

No rule was removed on the basis of this measurement. Roles are recorded
as strong / supporting / rare so that a future phase can tune weights
against evidence rather than intuition.

## 6. Ablation: fusion did not help

Grouped-split F1:

| Configuration | F1 |
|---|---|
| xgboost + heuristics @90% ML | 0.9966 |
| **xgboost only** | **0.9966** |
| xgboost + heuristics @70% ML | 0.9961 |
| heuristics only | 0.0729 |

ML-only matches or beats every fused variant. Reported as measured.

---

## 7. Calibration and threshold

- XGBoost is already well calibrated (Brier 0.0023); Platt improves it
  marginally to 0.00226. Isotonic helps the tree models but not the
  selected one. Calibration is therefore **not applied by default**.
- The operating threshold (~0.9965) is tuned on the validation fold for
  a 0.90 recall floor. It does not transfer to a differently-balanced
  corpus.

---

## 8. Statistical and methodological

| Limitation | Detail |
|---|---|
| Single training corpus | All in-domain results are PhiUSIIL-specific |
| No hyperparameter search | Default parameters for tractability; not tuned |
| Single split seed | `random_state=42`; no seed-variance estimate |
| Grouped split is approximate | Group stratification is inexact when a domain holds one class |
| Permutation importance on a sample | Validation data, not the full fold |
| One external corpus | May share collection methodology with the training corpus |
| No temporal split | Cannot measure decay on newly-registered domains |

---

## 9. Adversarial considerations

**No adversarial robustness testing has been performed.** An attacker
who knows the 39 features could construct URLs that evade them — for
example, matching the character-frequency profile the model associates
with phishing, or avoiding paths (since a path raises the score).

This is a known weakness of feature-based URL classifiers and is listed
because it is a property of the approach, not an oversight.

---

## 10. Privacy and ethical considerations

| Consideration | Position |
|---|---|
| Data submitted to BASIRAH | A URL string, analysed locally. No request is made to it. |
| Data retention | None. The API is stateless. |
| Third-party services | None. No external API is called. |
| Datasets | Public research corpora under their stated licences (CC BY 4.0, CC BY-NC-SA 4.0). |
| False positives | Severe — 9/13 real legitimate URLs flagged (§1.2). |
| Bias | The model inherits its corpus's profile of what phishing looks like. |

The **false-positive** burden deserves emphasis. A tool that flags
github.com and Mozilla documentation trains users to ignore it
immediately, and the harm falls on the legitimate sites being defended.

---

## 11. What would most improve this work

Ordered by expected value:

1. **Multi-corpus training.** Fixes §1.2 and §1.3 together. The single
   highest-value change.
2. **A corpus-quality audit gate.** Corpus audits must check path
   presence, feature-direction stability, and label orientation
   *before* training. All three defects were found only after.
3. **Domain-age features**, which address §1.2 directly and are a
   strong phishing indicator.
4. **Temporal split evaluation.**
5. **Character n-grams**, which may transfer better than length ratios.
6. **Recalibrate the heuristic rules** against measured behaviour.
7. **Adversarial evaluation** to establish the robustness floor.

---

## 12. Statement for the report

> BASIRAH Phase 2B implements a complete, reproducible and
> leakage-controlled machine-learning pipeline for URL phishing detection,
> achieving ROC-AUC 0.998 on a held-out, domain-grouped split of the
> PhiUSIIL corpus (235,362 URLs; 39 features generated by the production
> feature extractor).
>
> Through cross-dataset evaluation and corpus-quality auditing, the work
> additionally establishes three specific defects in the training corpus:
> an inverted label encoding, a complete absence of path-bearing URLs
> in the legitimate class, and inverted feature associations across 20 of
> 39 model inputs. The resulting model does not generalize: ROC-AUC falls
> to 0.271 on an independent corpus, and it misclassifies 9 of 13
> well-known legitimate URLs.
>
> All findings are reported. BASIRAH is presented as an explainable
> research prototype with a rigorously measured generalization gap, and
> the corpus-quality findings are offered as a reusable contribution in
> their own right.