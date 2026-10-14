# BASIRAH — Limitations (Internal Drafting Reference)

> Purpose: document scientifically true limitations. This is a no-fabrication
> section: it must state what the system cannot do, plainly.

---

## 1. Image AI Detection Is Advisory / Research-Grade

- No evaluated detector met the **production deployment criteria**.
- The system does **not** present image AI detection as solved.
- Image-AI verdicts are guidance, not certified or legally-verified
  authenticity.

---

## 2. Datasets

- **No real labelled phishing dataset is present** in the repository.
- Real corpora (Flickr30k, CommunityForensics) are licensed and excluded;
  only provenance manifests and audits are tracked.
- The only present data artifact is a dev fixture (`dev_fixture_urls.csv`),
  which is pipeline-only and explicitly cannot support conclusions.

---

## 3. No Persistent Relational Data Model

- BASIRAH does not use a persistent relational database; no SQL database
  exists. Any ERD must be marked "not applicable / limited."

---

## 4. No URL Browsing / No File Execution

- Submitted URLs are **not** automatically browsed or fetched.
- Uploaded files are **not** executed.

---

## 5. Missing Data Acquisitions

- Real labelled phishing dataset acquisition is pending.
- Real image corpora (Flickr30k, CommunityForensics) are licensed and
  excluded; the corpus can only be rebuilt from recorded URLs + checksums.

---

## 6. Language

- The project is English + Arabic (RTL) for the UI and content.
- Operating-language content (e.g. comparison tables, evaluation write-ups)
  should prefer English to avoid Arabic-translation variability, unless a
  bilingual edition is specifically requested.

---

## 7. Academic Positioning

- BASIRAH is a **defense advisory** demonstration, not a certified
  forensic/compliance tool.
- The report should state this explicitly and should not overclaim
  operational readiness.
