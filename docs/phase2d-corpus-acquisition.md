# Phase 2D — Corpus Acquisition

> Feeds **Chapter 5 — Methodology** (dataset section).
>
> Provenance for every Phase 2D source, including the ones that failed.

---

## 1. Objective

Acquire a legitimate URL corpus whose structure resembles the modern
web, to correct the defect measured in Phase 2B:

> **0 of 134,850** legitimate PhiUSIIL URLs carry a path.

The consequence was severe: a model trained on it learned *"has a path ⇒
phishing"* and flags `docs.python.org`, `github.com/anthropics` and
`developer.mozilla.org` as phishing. Baseline measured before this
phase: **10 of 14** well-known legitimate URLs flagged.

---

## 2. Requirement

The new corpus must contain:

documentation paths · repository paths · package registries ·
university pages · academic URLs · government portals · corporate
support pages · e-learning · video/watch · search/query · deep nesting ·
query strings · fragments · encoded parameters · subdomains · long URLs

And it must **not** be predominantly bare domains.

---

## 3. Sources attempted

### 3.1 Preferred — UNB CIC-URL-2016 (ISCX-URL2016)

The canonical academic benign corpus, and the first choice.

| | |
|---|---|
| Attempted | `http://205.174.165.80/CICDataset/CIC-URL-2016/CIC_2016_URLCSVs.zip` |
| Outcome | 301 → 302 → HTML landing page |

The download is now **gated behind a request form**. Not obtainable
without registration, which this project does not do.

### 3.2 CIC CSED2020

`https://cicresearch.ca/CICDataset-202011/Dataset/CSED2020.csv` returned
HTTP 200 with **HTML, not CSV**.

### 3.3 Common Crawl via `vonpower/PhishingDataset`

A well-documented Common Crawl legitimate corpus (800k Alexa-domain
URLs). The repository contains **only a README and two images**; no data
files are published.

### 3.4 Tranco top-1m — acquired, but NOT usable for this purpose

| | |
|---|---|
| Source | `https://tranco-list.eu/top-1m.csv.zip` |
| Size | 9,689,435 bytes |
| Rows | 1,000,000 domains |

Measured structure:

| Metric | Value |
|---|---|
| % with path | **0.00%** |
| % with query | **0.00%** |
| Median path depth | 0 |

**Tranco contains no path information at all.** It is a ranked domain
list, nothing more. It cannot fix the defect Phase 2D exists to address.

Tranco is therefore retained as a **domain-diversity reference only** and
is **excluded from training**. Its value here is negative evidence: it
demonstrates that "a list of popular domains" is not a substitute for a
realistic URL corpus, and that source choice must be measured.

### 3.5 PhishTank online-valid — acquired and used

| | |
|---|---|
| Source | `http://data.phishtank.com/data/online-valid.csv` |
| Size | 14,336,551 bytes |
| Rows | 74,997 |
| Licence | PhishTank terms; publicly downloadable |
| Labels | **All phishing**, human-verified |

Measured structure: **60.51% with a path**, 11.79% with queries.

This is the highest-confidence phishing source available — PhishTank
rows are contributor-verified, not inferred.

---

## 4. Primary legitimate corpus

| | |
|---|---|
| Dataset | `ealvaradob/phishing-dataset`, `urls.json` subset |
| Source | <https://huggingface.co/datasets/ealvaradob/phishing-dataset> |
| Direct | `.../resolve/main/urls.json` |
| Size | 73,157,496 bytes |
| SHA-256 | `32cfba42892c915b041a3f0ca6ffd0f484b2590c4c2ca91b13d3ea1330b2c9bd` |
| Licence | **Apache-2.0** |
| Gated | No |
| Last modified | 2024-01-31 |

### 4.1 Label semantics — documented, not assumed

The dataset card states explicitly:

> *"all records are labeled as **1 (Phishing)** or **0 (Benign)**"*

So the encoding is declared, not inferred. Phase 2B's inverted-label
defect arose precisely from assuming an encoding; the same discipline
applies here.

**Upstream provenance.** The uploader compiled four sources (mail, SMS,
URL, HTML). This file is the **URL subset only**, itself compiled from the
Kaggle corpus `harisudhan411/phishing-and-legitimate-urls` (>800,000
URLs). The proportion contributed by each upstream source is unknown.

### 4.2 The assumption being made

> **Legitimate labels are upstream-curated, not verified.**
>
> "Benign" is taken as labelled by the upstream corpus. **No independent
> verification of any individual URL was performed**, and none is possible
> without visiting URLs — which this project does not do.

This is weaker provenance than PhishTank's human verification, and is
recorded as such rather than presented as equivalent.

### 4.3 Measured structure — the reason it was selected

| Metric | Legitimate | Phishing |
|---|---|---|
| Rows | 444,916 | 390,763 |
| **% with a path** | **87.58** | 46.41 |
| % with a query | 11.78 | 11.77 |
| % HTTPS | 6.58 | 29.19 |
| Median path depth | 2 | 2 |
| Distinct registered domains | 111,805 | 194,723 |

### 4.4 The defect this corrects

| Corpus (legitimate class) | % with path |
|---|---|
| PhiUSIIL | **0.00** |
| **Phase 2D corpus** | **87.58** |

This is the central measurement of Phase 2D.

---

## 5. A limitation in the new corpus

Only **6.58%** of its legitimate URLs use HTTPS, against ~95%+ in real
web traffic. PhiUSIIL legitimate was similarly low, and MUD was 92%.

The consequence is concrete: in every corpus, HTTPS is far more
prevalent among phishing URLs than legitimate ones. A model trained on
any of them can learn HTTPS as a phishing signal — **which is exactly the
inversion Phase 2B found and had to work around by excluding the scheme
features entirely.**

The new corpus does not fix this, and could reinforce it. It is measured
and recorded rather than silently accepted, and the scheme features
remain excluded from model input for the reason established in Phase 2B.

---

## 6. Manifest

Full provenance, checksums, assumptions, selection methods and known
limitations for every source — including the failed ones — is recorded in:

```
backend/datasets/manifests/phase2d_legitimate_sources.json
```

---

## 7. Summary

| Source | Role | Path % | In training? |
|---|---|---|---|
| HF phishing URLs | realistic legitimate + phishing | 87.58 | **yes** |
| PhishTank | verified phishing | 60.51 | **yes** |
| Tranco | domain diversity reference | 0.00 | **no** |
| CIC-URL-2016 | — | — | unavailable |
| CSED2020 | — | — | unavailable |
| Common Crawl (vonpower) | — | — | unavailable |