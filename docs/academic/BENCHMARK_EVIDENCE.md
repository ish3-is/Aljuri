# BASIRAH — Benchmark Evidence (Internal Drafting Reference)

> Purpose: preserve the scientifically correct benchmark conclusions.
> **No evaluated image detector met the production deployment criteria.**

---

## 1. Detectors Evaluated

| Detector | Role | Status |
|---|---|---|
| **Detector A** | Production image detector (one of the ensemble) | **VERIFIED** |
| **Detector B** | Production image detector (the other ensemble member) | **VERIFIED** |
| **UnivFD candidate** | Research candidate evaluated where applicable | RESEARCH RESULT |

---

## 2. Holdout Limitations

- A held-out challenger set (blind defense test, Phase 37) was used to
  evaluate detector agreement on images the production stack had not seen in
  the training loop.
- A dev fixture URL corpus is **not** a dataset and cannot support
  conclusions (see `DATASET_EVIDENCE.md`); a model trained on it is
  pipeline-only unless explicitly forced, and even then marked
  `evaluated:false`.

---

## 3. False-Positive / False-Negative Findings

These are recorded in the benchmark/evaluation artifacts
(`backend/results/phase37/`). Note the project's explicit caveat: **no
evaluated detector met the production deployment criteria**, so any errors
on those evaluators are reported as research findings, not as delivered
performance.

---

## 4. Coverage / Abstention Tradeoffs

- The evidence service produces a **coverage score** (`coverage.detectorB`)
  and a coverage section.
- The URL model can enter an abstention state: it does not fabricate a
  distribution when uncertainty is high.
- Coverage and abstention are reported in the evidence view and asserted by
  frontend verification tests.

---

## 5. Deployment Criteria

**No evaluated image detector met the production deployment criteria.**

Consequently:

- Image AI detection is presented as **advisory / research-grade** only.
- The system does **not** claim image AI detection is solved.
- The report must say BASIRAH is **advisory**: it may point a user toward a
  likely-real / likely-synthetic classification, but it does not assert
  legally-verified authenticity.

---

## 6. Final Advisory-Only Recommendation

- Keep the detectors as **research / advisory** tooling.
- Do not present as a certified or forensic image-authenticity service.
- Document the limitation clearly in the report (scientific honesty).
