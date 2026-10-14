# BASIRAH — Dataset Evidence (Internal Drafting Reference)

> Purpose: document the datasets actually used, with purpose/source/sample /
> train/test role / limitations / source-family risk. **No datasets that were
> merely considered but not used are described.**

---

## 1. Summary

| Dataset | Purpose | Real in repo? | Status |
|---|---|---|---|
| `dev_fixture_urls.csv` | **Dev fixture only** — pipeline verification | Yes (infrastructure) | DEV_FIXTURE_ONLY, not a dataset |
| Image corpora (Flickr30k, CommunityForensics) | Evaluation | No — licensed, excluded | **NOT present** |
| Real labelled phishing dataset | Production model training | No | **NOT present** |

---

## 2. dev_fixture_urls.csv — DEV_FIXTURE_ONLY

**This file is not a dataset and cannot support any conclusion.**

- **Purpose:** prove the URL-model training pipeline runs.
- **Sample role:** 20 hand-written rows.
- **Train/test/holdout role:** none (it is a pipeline fixture).
- **Limitations:** not collected from a real dataset, not sampled, not
  representative; any metrics produced from it are meaningless.
- **Source-family risk:** none (it is a synthetic fixture, deliberately
  non-representative).
- **In production or only evaluation:** neither; it is a pipeline fixture.

The training script refuses to use it without `--allow-dev-fixture`. When
forced, the resulting model is marked `evaluated:false` with a WARNING. This
result must **not** be reported in the graduation document.

---

## 3. Image Corpora (Flickr30k, CommunityForensics) — NOT Present

- These are **licensed image corpora** used for evaluation.
- They are NOT downloaded/redistributed in this repository.
- What IS tracked: provenance manifests and audits (recorded URLs + checksums)
  so the corpus can be rebuilt.
- **Status: real image corpora are evaluated, but not present in the repo.**

---

## 4. Real Labelled Phishing Dataset — NOT Present

- No labelled phishing dataset is bundled with the repository and none was
  downloaded.
- The `datasets/` directory contains only infrastructure plus the dev fixture.
- **Status: real dataset acquisition is pending dataset acquisition.**

This is a first-order limitation of the project as delivered: **no production
training dataset is present**, so production-trained models are not assured.
The evaluation artifacts that DO exist (blind defense test, detector
evaluations, cross-family/robustness experiments) are the scientifically
supported baselines.

---

## 5. Source-Family Risk

| Source family | Risk | Handling |
|---|---|---|
| Dev fixture URLs | None (synthetic) | Pipeline-only |
| Flickr30k / CommunityForensics | Licensed, not redistributable | Manifests + checksums only |
| Real phishing corpus | Licensed, third-party | Pending acquisition |

---

## 6. Production vs. Evaluation

| Role | Artifacts present |
|---|---|
| **Production** | Real URL model; the image detectors (advisory only) |
| **Evaluation** | Blind defense test, detector evaluations, cross-family/robustness experiments |
| **Pipeline verification** | `dev_fixture_urls.csv` (refused without flag) |
