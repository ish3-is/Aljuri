# Phase 2B — Dataset Audit

> Provenance, integrity and schema validation for the datasets used to
> train and externally validate BASIRAH's URL classifier.
>
> **All counts in this document are measured by the audit code, not
> estimated.** The audit is reproducible: `scripts/run_phase2b_experiment.py`
> regenerates every figure below and writes the machine-readable form to
> `backend/results/phase2b/dataset_summary.json`.

---

## 1. Why the audit exists

A model's reported performance is a statement about a dataset before it is
a statement about a model. Before any training, the questions that must be
answered are:

1. **Where did this data come from, and is it legitimate to use?**
2. **What exactly does each row contain?**
3. **How is it distributed?** A phishing corpus skewed toward one attack
   style will not generalise.
4. **Is it internally consistent?** The same URL carrying two different
   labels means the labels are not ground truth.
5. **Is it suitable for the model that will be built on it?** Specifically:
   are its features available at inference time?

Point 5 is the one that most often goes unexamined, and it is addressed
explicitly in §3.

---

## 2. Primary dataset — PhiUSIIL

| Property | Value |
|---|---|
| Name | PhiUSIIL Phishing URL (Website) |
| Source | <https://archive.ics.uci.edu/dataset/967/phiusil-phishing-url-dataset> |
| Direct download | <https://archive.ics.uci.edu/static/public/967/data.csv> |
| Repository | UCI Machine Learning Repository, dataset id 967 |
| Creators | Arvind Prasad, Shalini Chandra |
| Publication date | 2020 |
| Licence | CC BY 4.0 (per UCI listing) |
| File size | 56,854,345 bytes |
| SHA-256 | `a236549cd369cd80bd478ff8e1779cbf44c58d5c3f79f7a51a1adbed7d06d1c6` |
| Columns in file | 56 (1 `FILENAME` + 54 features + `URL` + `label`) |
| Rows in file | **235,795** |

Row count matches the count published by UCI, so the file is complete.

### 2.1 Columns used

| Column | Role |
|---|---|
| `URL` | The raw URL — the **only** input to the model |
| `label` | See §2.2 — **the encoding is counter-intuitive** |

The remaining 54 columns are **deliberately ignored**. See §3.

### 2.2 Label encoding — `1 = legitimate`, `0 = phishing`

**This is the inverse of the near-universal convention and must be
stated explicitly.**

From the UCI dataset page: *"Label 1 corresponds to a legitimate URL,
label 0 to a phishing URL."*

The peer-reviewed literature confirms and repeats the need to invert it.
From Frontiers in Computer Science (2026): *"The original PHIUSIIL
labels follow a convention in which 1 denotes legitimate and 0 denotes
phishing. We invert this so that 1 denotes phishing."*

Verified directly against the data:

| Label | Meaning | Count | Example URLs |
|---|---|---|---|
| **0** | **phishing** | 100,945 | `www.f0519141.xsph.ru`, `www.shprakserf.gq`, `kuradox92.lima-city.de` |
| **1** | **legitimate** | 134,850 | `www.uni-mainz.de`, `www.rewildingargentina.org`, `www.teramill.com` |

BASIRAH passes `label_orientation=-1` to the audit, which flips the
column so the codebase uses `1 = phishing` internally. The orientation
is recorded in the manifest rather than assumed at training time.

> **Phase 2B ran once on the assumed convention.** The resulting model
> scored `google.com` at 99.9% phishing and the actual phishing URLs at
> 0%, while reporting AUC 0.998 — because every metric was computed
> against the same inverted labels. `LabelOrientationError` now aborts
> any audit whose numeric orientation is unstated, and
> `tests/test_phase2b_semantics.py` asserts on prediction *meaning*.

### 2.2a A second structural artifact: legitimate URLs have no path

| Class | Rows | With a path |
|---|---|---|
| phishing | 100,945 | 27,451 (**27.2%**) |
| legitimate | 134,850 | **0 (0.0%)** |

**Zero.** Not one of the 134,850 legitimate URLs contains a path. This
makes "carries a path" a near-perfect training proxy for phishing, and
the trained model accordingly misclassifies real-world legitimate URLs
that have paths — `github.com/anthropics`, `docs.python.org`,
`developer.mozilla.org`.

Measured effect: **9 of 13 well-known legitimate URLs are flagged.**
Removing the path-derived features does not fix it (see
`results/phase2b/path_artifact_experiment.csv`). Recorded as a known
defect in the test suite. This is the strongest single argument for
multi-corpus training in Phase 2C.

### 2.3 Cleaning outcomes

Measured in this order, and each row is counted once at its first failure:

| Stage | Count | Share of raw |
|---|---|---|
| Rows in file | 235,795 | 100% |
| Null URLs | 0 | 0% |
| Null labels | 0 | 0% |
| Unrecognised labels | 0 | 0% |
| **Malformed URLs** (rejected by the normaliser) | **8** | 0.0034% |
| **Duplicate rows** (same normalised URL) | **425** | 0.180% |
| **Conflicting labels** (one URL, both labels) | **0** | 0% |
| **Rows retained** | **235,362** | **99.82%** |

**Conflicting labels: zero.** This is a meaningful result. It means PhiUSIIL
does not contain the same URL labelled both ways, so its labels are at
least internally consistent — a property the secondary dataset does not
share (§4).

Note on ordering: duplicates are counted *after* normalisation, so two
spellings of the same URL (`example.com` and `http://example.com/`) count
as one. Duplicate detection on the raw string alone would have missed
them.

### 2.4 Final class distribution (retained rows, BASIRAH internal encoding)

| Label | Meaning | Count | Share |
|---|---|---|---|
| 0 | legitimate | 134,850 | 57.28% |
| 1 | phishing | 100,512 | 42.72% |
| | **total** | **235,362** | 100% |

The 433-row difference from the raw file is the 425 duplicates plus the
8 malformed URLs. Note the counts are **transposed** relative to the raw
file because of the orientation flip described in §2.2.

`class_weight="balanced"` is applied so the models do not inherit a
prior from this ratio.

### 2.5 Structural composition

| Property | Value |
|---|---|
| Distinct registered domains | **175,508** |
| Top-level domains | 683 |
| Domains appearing more than once | **5,964** |
| `https` | 183,728 (78.1%) |
| `http` | 51,634 (21.9%) |
| Other schemes | 0 |

The single most consequential number here is **5,964 domains appearing more
than once**. Those 5,964 families are where a random train/test split can
leak: if `login.example.com` lands in training and `verify.example.com`
lands in testing, the model has effectively seen the test domain. This is
the motivation for the grouped split (§5) and the reason Phase 2B evaluates
under both strategies.

### 2.6 Most repeated domain families

| Registered domain | URLs in file |
|---|---|
| `square.site` | 1,187 |
| `dweb.link` | 959 |
| `xsph.ru` | 928 |
| `pantheonsite.io` | 891 |
| `google.com` | 782 |
| `godaddysites.com` | 770 |
| `duckdns.org` | 642 |
| `webwave.dev` | 559 |
| `weebly.com` | 552 |

These are free-hosting and dynamic-DNS platforms. Their presence in bulk is
itself a dataset artefact: legitimate URLs hosted on such platforms look
structurally unusual, and their volume shapes what a model learns. This is
not a defect of the dataset, but it is a **bias a reader of Chapter 7
should know about**.

---

## 3. Feature-suitability decision — the most important audit finding

PhiUSIIL ships 54 precomputed features. They are **not** used.

Reason: many are derived from the **webpage**, not the URL:

| PhiUSIIL column type | Example columns | Available in URL-only inference? |
|---|---|---|
| Page-content counts | `NoOfExternalRef`, `NoOfSelfRef`, `NoOfEmptyRef` | **No** |
| Page text statistics | `LargestTextLength`, `AvgTextLength` | **No** |
| HTML structure | (several page-structure columns) | **No** |
| Keyword-in-HTML | page keyword presence | **No** |
| Response-time proxies | (timing-derived columns) | **No** |
| Purely lexical | `URLLength`, `NoOfSubDomain`, `TLDLegitimateProb`, … | Yes, but recomputed anyway |

BASIRAH's production pipeline is **URL-string-only by design** (Phase 2A):
it parses a URL and never fetches a page. Training on page-derived features
would therefore create **training-serving skew** — the model would depend
on signals that do not exist when it runs, and its measured accuracy would
not transfer to production.

The mandated pipeline is therefore:

```
PhiUSIIL raw URL
      ↓
BASIRAH normalisation      app/services/url_analyzer.py
      ↓
BASIRAH feature extractor  app/services/feature_extractor.py
      ↓
41-feature vector
      ↓
ML model
      ↓
live inference — identical code path
```

The **same function** (`extract_features`) generates training inputs and
serving inputs. There is no notebook-only extractor. This is enforced, not
merely intended:

- `app/ml/feature_schema.py` records the ordered feature list, the
  extractor version, and a fingerprint of both.
- Training asserts the live extractor produces exactly that schema.
- Inference asserts the same before loading a model.
- A mismatch in the feature **set** *or its **order*** raises
  `FeatureSchemaMismatch` and the model is refused. Order mismatch is the
  dangerous case: it passes every set comparison and silently feeds
  permuted input.

---

## 4. Secondary dataset — Malicious URL Detection Enhanced 2026

| Property | Value |
|---|---|
| Name | Malicious URL Detection Dataset Enhanced 2026 |
| Source | <https://www.kaggle.com/datasets/moutasmtamimi/malicious-url-detection-dataset-enhanced-2026/data> |
| Creator | moutasmtamimi (Kaggle) |
| Licence | CC BY-NC-SA 4.0 (per Kaggle listing) |
| Download size | ~163 MB (zip), 377,869,564 bytes uncompressed CSV |
| Containing file | `MUD_malicious_urls_2026_V2.csv` |
| Columns | 100 |
| Rows | 632,845 |

### 4.1 Schema inspection (before any use)

The schema was inspected rather than assumed. Relevant columns:

| Column | Meaning |
|---|---|
| `url` | Raw URL |
| `class_label` | Textual class: `benign` / `defacement` / `phishing` / `malware` |
| `label` | Integer encoding: 0 / 1 / 2 / 3 |
| `source_dataset` | Provenance of the row |
| `reachability_class` | Whether the host was reachable when collected |
| `is_syntax_valid` | Syntax check |

The integer encoding was verified empirically rather than trusted:

| `class_label` | `label` | Count (400k sample) |
|---|---|---|
| benign | 0 | 297,883 |
| defacement | 1 | 74,726 |
| phishing | 2 | 24,227 |
| malware | 3 | 3,164 |

**This dataset is not binary.** It has four classes.

### 4.2 The comparability decision

Only `benign` and `phishing` rows are used for external validation.
`defacement` and `malware` rows are **excluded**.

Reason: BASIRAH's task is phishing-versus-legitimate. Defacement (site
hijacking) and malware distribution are different threat classes with
different URL characteristics. Folding them into the phishing class would
test the model against a target it was never trained for, and the resulting
score would understate it for reasons that have nothing to do with
generalisation. That is not a real measurement.

### 4.3 Additional dataset properties observed

| Property | Value |
|---|---|
| `reachability_class` = `unreachable_or_unscanned` | 82.4% of a 300k sample |
| `is_syntax_valid` = `True` | 100% of sample |
| `source_dataset` | Single value: `final_dataset_with_all_features_v3_1` |

The high unreachable share is worth recording: most rows were classified
without a live fetch. Combined with the fact that the corpus already
contains the kinds of lexical features BASIRAH computes, this raises the
question of whether the two datasets share collection methodology — which
would make the external validation less independent than it appears. That
caveat belongs in Chapter 7 and is discussed in
`phase2b-generalization.md`.

Note also that this dataset's 100 columns include many features similar in
spirit to BASIRAH's (`url_entropy`, `host_entropy`, `digit_ratio`,
`subdomain_count`, `has_punycode`, `is_ip_host`, `tld`, `is_https`). **None
of them are used.** Only `url` and `class_label` are read, and features are
regenerated by BASIRAH's extractor — the same discipline applied to
PhiUSIIL.

---

## 5. Leakage policy

The audit establishes that PhiUSIIL contains 5,964 repeated domain
families. Two evaluation strategies are therefore mandatory.

### 5.1 Random stratified split

The conventional academic setup. Domains are *expected* to span partitions.
No leakage assertion applies — the optimism it produces is precisely what
the second strategy measures.

### 5.2 Grouped-domain split

All URLs sharing a registered domain are placed in the same partition.
Implemented with `StratifiedGroupKFold` (`app/ml/splits.py`).

```
login.example.com   ┐
verify.example.com  ├─ registered domain "example.com" ── one partition
example.com/reset   ┘
```

A `DomainLeakageError` is raised if any domain appears in more than one
partition — the experiment **aborts** rather than reporting metrics from a
leaked split. The result is recorded in
`results/phase2b/split_summary.json` under `leakage_proof`.

---

## 6. Audit summary

| Finding | Consequence |
|---|---|
| PhiUSIIL has 235,795 rows, 57.18% phishing | Sufficient for training; mild imbalance handled with `class_weight="balanced"` |
| 425 duplicates, 8 malformed, 0 conflicts | 235,362 usable (99.82%) |
| **Zero conflicting labels** | PhiUSIIL labels are internally consistent |
| **5,964 repeated domain families** | Random split will be optimistic; grouped split is mandatory |
| 175,508 distinct domains | Genuine variety; domain memorisation is limited but possible |
| 54 precomputed features ignored | No training-serving skew; see §3 |
| Secondary dataset is **4-class** | Only benign/phishing comparable; defacement/malware excluded |
| Secondary dataset may share collection methodology | Limits how independent external validation is |

---

## Reproducing

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.\.venv\Scripts\python.exe -m scripts.run_phase2b_experiment
```

Raw files in `datasets/raw/` are never modified. Manifests with SHA-256
checksums are written to `datasets/manifests/`. Cleaned output goes to
`datasets/processed/`.
