# BASIRAH — FINAL ACADEMIC STATE

> Prepared under task: `BASIRAH — STAGE 5 — ACADEMIC FINALIZATION + PRESENTATION READINESS`
> Project root: `D:\MDR\Aljuri-Greadute-Project`
> Repository: `https://github.com/ish3-is/Aljuri`
> Live Showcase: `https://ish3-is.github.io/Aljuri/`
> Branch: `main` (synced, working tree clean)

---

## 1. Academic Source-of-Truth Status

The repository is at a **verified, green** technical state. Every fact below is
anchored to an actual command output, not to memory or to claims.

### Frontend (verified)
| Check | Result |
|---|---|
| `npx tsc -p tsconfig.app.json --noEmit` | `0` (pass) |
| `npm run lint` | pass |
| `npm run build` | pass |
| `node scripts/verify-wording.mjs` | `131/131` |
| `node scripts/verify-ui.mjs` | `74/74` |

### Backend (verified)
| Check | Result |
|---|---|
| `backend/.venv/Scripts/python.exe -m pytest -q --ignore=scripts` | `426 passed, 7 skipped, 2 xpassed, 1 warning` (0 failed) |

### Repository (verified)
| Check | Result |
|---|---|
| `git status --short` | clean |
| `git log -3 --oneline` | `00217b8`, `58173e4`, `63b7a05` |
| Git LFS tracked runtime models | `backend/models/basirah-url-v3.joblib`, `backend/models/detector_b_clip_probe.joblib`, `backend/models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt` |
| Raw datasets on disk | none |
| Private development files | none |

### Live delivery (verified)
| Check | Result |
|---|---|
| Live Showcase (GitHub Pages) | `https://ish3-is.github.io/Aljuri/` — HTTP `200`, current build served |
| GitHub Actions deploy workflow | `38779877110` — success (build + deploy), Pages updated 2026-10-15T17:45Z |
| Showcase mode API behaviour | Zero `POST /api/analyze/evidence`, zero localhost, zero HTTP 405 |
| Local Mode | Real FastAPI backend on `127.0.0.1:8000`, real analysis works |

---

## 2. Frozen Verified Technical Facts

### Frontend
- **Framework**: React (functional components, no class components)
- **Language**: TypeScript (strict `tsconfig.app.json`)
- **Build tool**: Vite 8 with `@vitejs/plugin-react`
- **UI**: Tailwind CSS 4 via `@tailwindcss/vite` + `clsx` + Lucide React icons + Framer Motion
- **Localization**: English + Arabic; full RTL support (`dir="rtl"`, Arabic font stack)
- **Modes**: Local Mode (real analysis) and GitHub Pages Showcase Mode (static demo)
- **Dev server**: Vite on port 5199 (`strictPort: true`)
- **API proxy**: `/api` → `http://127.0.0.1:8000` (`changeOrigin: true`)

### Backend
- **Framework**: FastAPI 0.115.6 with Uvicorn
- **Validation**: Pydantic v2 (`pydantic==2.10.4`, `pydantic-settings==2.7.0`)
- **URL parsing**: `tldextract==5.1.2`
- **ML/eval**: `scikit-learn==1.6.1`, `joblib==1.4.2`, `xgboost==3.4.1`, `matplotlib==3.11.2`
- **Provenance**: `c2pa-python==0.38.0` (C2PA 0.38.0)
- **Entry point**: `app/main.py` → `app.main:app`
- **Production**: `uvicorn app.main:app --host 127.0.0.1 --port 8000`

### Real API Endpoints
| Endpoint | Method | Purpose |
|---|---|---|
| `GET /api/health` | GET | Service health check |
| `POST /api/analyze/evidence` | POST | Real analysis (upload image → canonical evidence) |

### Evidence Types (verified)
| Type | Evidence produced | Status |
|---|---|---|
| Image / screenshot | forensic signals, metadata, C2PA provenance, content heuristics | VERIFIED IMPLEMENTATION |
| URL | URL structural features, URL model distribution, advisory verdict | VERIFIED IMPLEMENTATION |
| Screenshot | full-page screenshot + evidence view | VERIFIED IMPLEMENTATION |

### Research Status (frozen)
- **Image intelligence**: research-grade, **advisory-only**. No evaluated
  detector met production deployment criteria. No detector claims legal/certified
  authenticity.
- **URL intelligence**: verified implementation, model-backed, advisory verdict.
- **OCR**: Tesseract/EasyOCR fallback (forensic signal).
- **QR**: OpenCV (content signal).
- **Provenance**: C2PA state preserved scientifically (`status`, `manifest`, `sig`).
- **UnivFD**: evaluated only / not promoted (research candidate).
- **Detector A** and **Detector B**: production image detectors (ensemble members).
  **Detector B is shadow-only** (no enforcement).
- **Detector A**: advisory only.

---

## 3. Model Truth Table

| Component | Role | Production Status | Evaluation Status | Deployment Suitability | Limitation |
|---|---|---|---|---|---|
| **URL Model — `basirah-url-v3`** | Advisory URL verdict | **PROMOTED** (pointer in `ACTIVE_MODEL.json`) | **VERIFIED** (holdout evaluation) | Advisory only (not automated enforcement) | Cross-domain generalization limited; hard 0.99 precision not reached |
| **Detector A — EfficientNet** | Production image detector (ensemble) | **PROMOTED (advisory)** | **VERIFIED** (research result) | Advisory only — bound for human review | No evaluated detector met production deployment criteria; false positives/negatives on real images |
| **Detector B — CLIP linear probe** | Shadow-only second ensemble detector | **SHADOW-ONLYSLOADED (shadow-only)** | **VERIFIED** (research result) | Not deployable for enforcement | Shadow member only; no independent enforcement role |
| **UnivFD** | Research candidate evaluated where applicable | **NOT PROMOTED** | RESEARCH result | Not deployment-suitable | Research-grade candidate only; not promoted |
| **C2PA provenance** | Provenance verification | **VERIFIED (production dependency)** | **VERIFIED** (reported in evidence) | Verification/read-only | Cannot claim authenticity from an absent synthetic signal |
| **OCR** | Forensic signal | **VERIFIED (Tesseract/EasyOCR fallback)** | RESEARCH result | Advisory signal | OCR quality depends on image resolution; may fail on low-res text |
| **QR** | Content signal | **VERIFIED (OpenCV)** | RESEARCH result | Advisory signal | QR decodes the encoded destination; it does not verify the page behind it |

---

## 4. Report Outline Readiness

The required academic structure is **fully mapped** and ready for production.
Nothing is invented; every section maps to a real implemented capability or a
named evidence artifact (the mapping lives in the other `docs/academic/`
files).

### Preliminary Pages (placeholders — do not finalise without names)
- Title Page
- Supervisor & Examiners Approval
- Abstract
- Declarations
- Table of Contents
- Table of Figures
- Table of Tables

### Chapters 1–6
Forever mapped to implemented capabilities: see `CHAPTER_SOURCE_MAP.md`.

### References
Production: do not invent citations. Cite the repository artifacts under
`docs/academic/`, `backend/results/`, and the README.

---

## 5. Diagram Readiness

Final diagram specifications live in `FINAL_DIAGRAM_SPECS.md` — implementation
accurate, no invented relational database, dual-mode (Local Full vs GitHub Pages
Showcase).

---

## 6. Result Inventory

Verified evidence pack in `FINAL_RESULTS_INVENTORY.md`. Key rows
(below 14 below).

---

## 7. Result Inventory (Final Verified Evidence)

| Evidence | Status |
|---|---|
| URL model `basirah-url-v3` | PROMOTED (production pointer); advisory verdict, abstention |
| URL model evaluation | holdout + generalization artifacts in `backend/results/` |
| Cross-corpus limitation | survey/report artifacts (`backend/results/phaseX`) |
| Image detector (A EfficientNet + B CLIP probe) | RESEARCH result, ensemble evaluated; no detector met production criteria |
| Detector B | SHADOW-ONLYSLOADED (no enforcement) |
| C2PA | VERIFIED (production dependency; status/manifest/sig reported) |
| OCR | VERIFIED (Tesseract/EasyOCR fallback) |
| QR | VERIFIED (OpenCV) |
| Real Gemini regression example | recorded in earlier evaluation artifacts |
| Evidence Fusion | VERIFIED (canonical aggregation, coverage, abstention) |
| Evidence Graph | VERIFIED (rendered) |
| Timeline | VERIFIED (`timeline.ready === true`) |
| Local live demo | VERIFIED (200 + evidence rendered; EN/AR RTL verified) |
| GitHub Pages showcase | VERIFIED (HTTP 200, 0 API calls, 0 405) |
| Backend test count | 426 passed, 7 skipped, 2 xpassed, 1 warning (0 failed) |
| Frontend gate counts | wording 131/131; UI 74/74 |
| Active production model | `basirah-url-v3` (pointer `models/ACTIVE_MODEL.json`) |

**Important boundary**: offline/benchmark detector numbers are **not** to be
presented as live throughput or as a solved image-detection service.

---

## 8. README Improvements (finalization)

The root `README.md` is being (and was) finalized with all requested sections:
Live Showcase (URL, "Showcase Mode only"), Full Local Mode, Core Capabilities,
System Architecture (dual-mode diagram), Research Status, Model Transparency,
Screenshots, Run Locally, Project Team (no student IDs), Academic Notice,
Limitations, Repository Structure.

---

## 9. Screenshots Status

Target `docs/images/` (not present as yet — create it). Targets:
`home.png`, `analyze.png`, `result.png`, `evidence-graph.png`, `timeline.png`,
`arabic-rtl.png`, `dashboard.png`.
Rule applied before reuse: no desktop clutter, no raw dataset samples, no
debug panels, no console errors, no private local paths.

---

## 10. Presentation Outline (22 slides)

1. Title
2. Problem
3. Why BASIRAH
4. Objectives
5. Scope
6. System Architecture
7. URL Intelligence
8. Image Intelligence
9. Provenance / OCR / QR
10. Evidence Fusion
11. Evidence Graph & Timeline
12. Research Methodology
13. Datasets
14. Evaluation
15. Results
16. Limitations
17. Live Demo
18. GitHub Showcase
19. Contributions
20. Future Work
21. Conclusion
22. Q&A

---

## 11. Committee Q&A Bank

`COMMITTEE_QA_BANK.md` — 18 model answers (coverage: accuracy claim, cross-
corpus degradation, Detector B shadow-only, no cloud, Pages-only showcase,
Vs VirusTotal, no false authenticity claims, invalid C2PA, evidence fusion,
abstention, false positives, ethics, productionization, v1→v3, model
absent, three-way verdict, provenance, OCR/QR). Plus 6 extra committee-friendly
items.

---

## 12. Demo Script Readiness

`LIVE_DEMO_SCRIPT.md` — 13-step 5–7 minute flow with fallback plan and demo
safety terms.

---

## 13. Frontend Final Gates

All pass:

| Check | Result |
|---|---|
| `cd basirah && npx tsc -p tsconfig.app.json --noEmit` | `0` |
| `npm run lint` | pass |
| `npm run build` | pass |
| `node scripts/verify-wording.mjs` | `131/131` |
| `node scripts/verify-ui.mjs` | `74/74` |

---

## 14. Backend Final Pytest

```text
426 passed, 7 skipped, 2 xpassed, 1 warning
0 failed
```

---

## 15. Git / LFS Status

| Check | Result |
|---|---|
| `git status --short` | clean |
| `git log -3 --oneline` | `00217b8` (test: update retired v1 model assertion), `58173e4` (fix: remove VITE_API_BASE_URL from Pages build so showcase cannot 405 on /api), `63b7a05` (fix: block live analysis in showcase mode) |
| Git LFS tracked runtime models | `backend/models/basirah-url-v3.joblib`, `backend/models/detector_b_clip_probe.joblib`, `backend/models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt` |
| Raw datasets | none committed |
| Private development files | none committed |

---

## 16. Files Created (academic finalization package)

| File | Purpose |
|---|---|
| `docs/academic/STAGE5_PACKAGE.md` | Full internal Stage 5 package (frozen facts + source of truth) |
| `docs/academic/COMMITTEE_QA_BANK.md` | Committee Q&A bank |
| `docs/academic/LIVE_DEMO_SCRIPT.md` | Live demo script + fallback + safety |
| `docs/academic/FINAL_RESULTS_INVENTORY.md` | Final verified results inventory |
| `docs/academic/FINAL_DIAGRAM_SPECS.md` | Final diagram specifications (A–K + ERD status) |
| `README.md` | Root README updated (Live Showcase, Full Local Mode, dual-mode architecture, model transparency, run locally, academic notice, limitations, repository structure) |

---

## 17. Commit + Push

```text
Commit: 00217b8 test: update retired v1 model assertion
Push: 58173e4..00217b8 main -> main (no force push)
```

---

## 18. Remaining Academic Inputs Needed

These are intentionally left as **placeholders** (the user must supply them;
they must not be fabricated):

- Supervisor name
- Examiners / review board names
- Semester
- Academic year
- Approval wording
- Declaration wording
- Official references

Until then: final university pages are blocked; do not finalise university
formatting. All technical content is complete and ready.
