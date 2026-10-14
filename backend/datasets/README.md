# DATASETS

## Status: no real dataset is present

**Real model evaluation is pending dataset acquisition.**

No labelled phishing dataset is bundled with this repository, and none was
downloaded. This directory contains infrastructure and one development
fixture only.

---

## `dev_fixture_urls.csv` — DEV_FIXTURE_ONLY

**This file is not a dataset and cannot support any conclusion.**

- 20 hand-written rows created to prove the training pipeline runs.
- Not collected from any real dataset, not sampled, not representative.
- Any metrics produced from it are meaningless.

The training script refuses to use it unless explicitly forced:

```powershell
# Refuses without the flag:
.venv\Scripts\python.exe -m scripts.train_url_model --data datasets\dev_fixture_urls.csv

# Forced, and the resulting model is marked evaluated:false with a WARNING:
.venv\Scripts\python.exe -m scripts.train_url_model --data datasets\dev_fixture_urls.csv --allow-dev-fixture
```

A model trained this way is for pipeline verification only. Do not report
its metrics in the graduation document.

---

## Expected format for a real dataset

A CSV with (at minimum) these two columns:

```csv
url,label
https://example.com,0
http://192.168.1.1/login,1
```

### Column names

The loader tolerates common variations:

| Purpose | Accepted column names |
|---|---|
| URL | `url`, `urls`, `uri`, `link` |
| Label | `label`, `labels`, `class`, `target`, `y`, `is_phishing` |

### Label values

Any of these vocabularies is accepted and normalised:

| Meaning | Accepted values |
|---|---|
| Phishing (1) | `1`, `true`, `yes`, `y`, `phishing`, `phish`, `malicious`, `bad`, `fraud`, `spam`, `1.0` |
| Benign (0) | `0`, `false`, `no`, `n`, `legit`, `legitimate`, `benign`, `good`, `safe`, `normal`, `0.0` |

An unrecognised label raises an error. It is never silently coerced to
`0`, because that would quietly poison the training set with mislabelled
benign rows.

### Quality requirements

The pipeline handles these automatically, but a dataset meeting them
produces better results:

1. **Class balance.** Report both counts. Heavy imbalance is legal, but
   accuracy becomes misleading and the stratified split matters more.
2. **Deduplication.** Exact duplicate URLs are dropped and counted in the
   dataset report.
3. **Normalised URLs.** If your source stores URLs with tracking
   parameters or fragments, strip them first. `?utm_source=...` adds
   length and entropy features that say nothing about the site.
4. **Label provenance.** Record where the labels came from and when they
   were assigned. Domains change hands; a dataset's age is a limitation
   worth stating in Chapter 8.
5. **Time-based split for the strongest claim.** A random split lets the
   model see near-duplicates of its training rows. If your dataset has a
   collection date, a chronological split is a more honest evaluation of
   performance on *new* URLs.

---

## Acquiring a dataset

Not done here, deliberately: silently downloading an unvetted dataset is
exactly the kind of step that quietly enters a project unreviewed.

When you choose one, record in this directory:

- source URL and licence
- collection date
- row count and class balance
- known biases (e.g. over-representation of one attack style)

Candidate sources commonly used in the literature include publicly
published phishing URL corpora from academic repositories. Verify the
licence permits your use before including it in a graduation submission.

---

## Training with a real dataset

Place the CSV in this directory, then:

```powershell
.venv\Scripts\python.exe -m scripts.train_url_model --data datasets\<your-file>.csv
.venv\Scripts\python.exe -m scripts.evaluate_url_model
```

The model bundle, its feature order and its metrics are written to
`models/`. `GET /api/model/info` then serves those metrics as
transparency metadata.
