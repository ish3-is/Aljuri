# BASIRAH — STAGE 5 ACADEMIC FINALIZATION PACKAGE

> Prepared under task: `BASIRAH — STAGE 5 — ACADEMIC FINALIZATION + PRESENTATION READINESS`
> Project root: `D:\MDR\Aljuri-Greadute-Project`
> Repository: `https://github.com/ish3-is/Aljuri`
> Live Showcase: `https://ish3-is.github.io/Aljuri/`
> Branch: `main` (synced, working tree clean)

This package documents the **current, verified technical state** so that the
final university report, slides, live demo, and committee Q&A bank are no
longer draft-and-guess work. It is an **internal drafting reference** — it is
NOT the final university-formatted report, and it contains no supervisor or
examiner names, semester, academic year, approval wording, declaration
wording, or official references (those are intentionally left as placeholders).

---

## 1. Academic Source-of-Truth Status

The repository is at a **verified, green** technical state. Every fact in this
package is anchored to an actual command output, not to memory or to claims.

Verified as of this package:

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
| Raw datasets on disk | none (no raw labelled phishing corpus committed) |
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

`/api/analyze/evidence` accepts `mode=auto` (production analysis) and returns the
full evidence payload (canonical verdict, provenance, evidence, graph, timeline,
coverage, traceability, metadata/forensics).

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
| **Detector A — EfficientNet** | Production image detector (ensemble) | **PROMOTED (advisory)** | RESEARCH result | Advisory only — bound for human review | No detector met production deployment criteria; false positives/negatives on real images |
| **Detector B — CLIP linear probe** | Shadow-only second ensemble detector | **SHADOW-ONLYSLOADED (shadow-only)** | RESEARCH result | Not deployable for enforcement | Shadow member only; no independent enforcement role |
| **UnivFD** | Research candidate evaluated where applicable | **NOT PROMOTED** | RESEARCH result | Not deployment-suitable | Research-grade candidate only; not promoted |
| **C2PA provenance** | Provenance verification | **VERIFIED (production dependency)** | **VERIFIED** (reported in evidence) | Verification/read-only | Cannot claim authenticity from an absent synthetic signal |
| **OCR** | Forensic signal | **VERIFIED (Tesseract/EasyOCR fallback)** | RESEARCH result | Advisory signal | OCR quality depends on image resolution; may fail on low-res text |
| **QR** | Content signal | **VERIFIED (OpenCV)** | RESEARCH result | Advisory signal | QR decodes the encoded destination; it does not verify the page behind it |

---

## 4. Report Outline Readiness

The required academic structure is **fully mapped** and ready for production.
Nothing is invented; every section maps to a real implemented capability or a
named evidence artifact (the mapping lives in `docs/academic/CHAPTER_SOURCE_MAP.md`).

### Preliminary Pages (placeholders — do not finalise without names)
- Title Page
- Supervisor & Examiners Approval
- Abstract
- Declarations
- Table of Contents
- Table of Figures
- Table of Tables

### Chapter 1 — Introduction
`1.1 Problem Statement` · `1.2 Aim and Objectives` · `1.3 Project Scope` ·
`1.4 Contribution` · `1.5 Report Outline`

### Chapter 2 — Background & Literature Review
`2.1 General Concepts` · `2.2 Core Domain / Technology` (`2.2.1 Advantages`,
`2.2.2 Limitations`) · `2.3 Detailed Technical Concepts` · `2.4 System
Classifications / Deployment Models` · `2.5 Detection / Processing Techniques &
Algorithm Selection` · `2.6 Related Work` · `2.7 Gaps and Project Justification`

### Chapter 3 — Methodology
`3.1 Introduction` · `3.2 Methodology / Framework` · `3.3 Development Stages`
(`3.3.1 Timetable`, `3.3.2 Gantt Chart`) · `3.4 Data and Evaluation`
(`3.4.1 Datasets / Data Collection`, `3.4.2 Evaluation Criteria`) · `3.5 Summary`

### Chapter 4 — System Analysis & Design
`4.1 Introduction` · `4.2 Requirements` (`4.2.1 Functional`, `4.2.2 Nonfunctional`) ·
`4.3 Use Case Diagram` · `4.4 Data Flow Diagram` · `4.5 ERD / Data Model` ·
`4.6 Sequence Diagram` · `4.7 Class / Component Diagram` · `4.8 Summary`

### Chapter 5 — Implementation & Results
`5.1 Introduction` · `5.2 Offline / Benchmark Results` · `5.3 Live System / Demo
Results` · `5.4 Discussion` · `5.5 Summary`

### Chapter 6 — Source Code & Appendices
`6.1 Web / Backend` · `6.2 Core Models` · `6.3 Training / Evaluation Scripts` ·
`6.4 Data / Schema` · `6.5 Dependencies` · `6.6 Styles / Templates`

**References**

---

## 5. Diagram Readiness

Diagram specifications below are **implementation-accurate** (no invented
relational database). Two independent delivery paths are shown so the report
does not conflate live inference with static showcase.

### A. System Architecture
```
LOCAL FULL MODE                          GITHUB PAGES SHOWCASE MODE
┌──────────────────────────┐              ┌──────────────────────────┐
│ User                     │              │ User                     │
│   │                          │              │   │                      │
│   ▼                          │              │   ▼                      │
│ React/Vite frontend      │              │ React/Vite frontend (static)│
│   │                          │              │   │                      │
│   ▼                          │              │   ▼                      │
│ FastAPI backend          │              │   (no backend)             │
│   │                          │              │                          │
│   ▼                          │              │   ▼                      │
│ runtime models           │              │   static sample result     │
│   │                          │              │   (showcase/result.tsx)  │
│ evidence fusion          │              │                          │
│   │                          │              │                          │
│ result/UI/report         │              │   NO real inference        │
└──────────────────────────┘              └──────────────────────────┘
```

### B. Use Case Diagram
Actor: **User**. Primary use cases:
1. **Submit URL** → get URL evidence + advisory verdict
2. **Analyze image** → evidence view (canonical verdict, provenance, forensics)
3. **Show provenance** → C2PA status/manifest/sig
4. **Inspect OCR signal** → OCR text
5. **Inspect QR signal** → decoded destination
6. **View evidence graph** → evidence graph (SVG)
7. **View analysis timeline** → stage timeline
8. **Select language** → EN / AR (RTL)
9. **View sample result** → static showcase result (GitHub Pages only)

### C. DFD Level 0 (context)
- **External agent**: User
- **Processes**: URL intake → evidence pipeline → URL analysis; Image intake →
  evidence pipeline → image analysis; Output → evidence/UI/report
- **Data stores**: evidence store (in-memory / transient); model store (runtime
  models); format schema store
- **Note**: NO persistent relational database exists in the system.

### D. DFD Level 1
Top-level decomposition of the evidence pipeline:
1. **Intake normalizer**: normalize URL; load image URL; read uploaded file
2. **Feature extractor**: URL features; file features (metadata, OCR, QR, forensics)
3. **Detectors**: Detector A (EfficientNet), Detector B (CLIP linear probe,
   shadow-only), UnivFD (research candidate, not promoted)
4. **URL model**: `basirah-url-v3` advisory distribution; abstention state
5. **Evidence fusion**: canonical aggregation, coverage, abstention accounting
6. **Output renderer**: EvidenceResultView (final assessment, provenance, graph,
   timeline, coverage, metadata/forensics, traceability, report)

### E. Sequence Diagram — Image Analysis
```
User
  │  1. select image (file upload)
  │  2. choose modality = image
  │  ▼
React/Vite front-end
  │  3. submit file to POST /api/analyze/evidence (mode=auto)
  │  ▼
FastAPI backend
  │  4. canonical evidence pipeline
  │       → features (metadata, OCR, QR, forensics, C2PA)
  │       → detector ensemble (A + B [shadow], UnivFD [research])
  │       → URL-model advisory distribution (v3)
  │       → coverage / abstention accounting
  │  ▼
  │  5. JSON evidence response (real HTTP 200)
  │  ▼
React/Vite front-end  (EvidenceResultView)
  │  6. render: final assessment, provenance, evidence, graph, timeline,
  │     coverage, metadata/forensics, traceability
  │  ▼
User
```

### F. Sequence Diagram — URL Analysis
```
User
  │  1. paste URL / submit URL
  │  ▼
React/Vite front-end (UniversalInput → analysis)
  │  2. POST /api/analyze/evidence (mode=auto, URL signal)
  │  ▼
FastAPI backend
  │  3. URL structural features + URL model (v3) advisory distribution
  │       (abstention if uncertainty high; no browsing/fetching of URL)
  │  ▼
  │  4. JSON evidence response (real HTTP 200)
  │  ▼
React/Vite front-end
  │  5. render: advisory verdict, URL evidence
  │  ▼
User
```

### G. Sequence Diagram — Showcase Mode
```
User
  │  1. open https://ish3-is.github.io/Aljuri/#/analyze
  │  ▼
React/Vite static front-end (GitHub Pages)
  │  2. VITE_APP_MODE = showcase → no /api call
  │  ▼
  │  3. render notice + static sample result
  │       (DEMO — SAMPLE RESULT via EvidenceResultView + SHOWCASE_RESULT)
  │  ▼
User
  (no real analysis, no backend, no inference)
```

### H. Evidence Fusion Flow
```
URL model advisory distribution
    + image forensics / metadata
    + C2PA provenance state (status, manifest, sig)
    + OCR text signal
    + QR decoded signal
    + Detector A / Detector B advisory outputs
    + coverage / abstention accounting
        │
        ▼
canonical verdict (trusted / uncertain / adversarial) + advisory confidence
        │
        ▼
Evidence → report
```

### I. Evidence Graph Flow
```
Evidence payload
  → nodes: signal sources (URL, image, provenance, OCR, QR, detectors)
  → edges: correlations (metadata↔OCR, QR↔destination, detector outputs, URL)
  → render EvidenceGraphView (SVG) + timeline + coverage
  → traceability IDs preserved
```

### J. Component/Class Diagram
- **URL architecture**: `app/api/routes.py` (`PUT /api/analyze/evidence`),
  `app/services/url_analyzer.py` (normalization, feature extraction, model
  interface), `app/ml/production.py` (`ProductionModel`, `load_production_model`),
  `app/ml/model_loader.py` (`ModelBundle`, `ModelStatus`).
- **Image architecture**: `app/image/ensemble/detector_a.py` (EfficientNet),
  `app/image/ensemble/detector_b.py` (CLIP linear probe, shadow-only),
  `app/image/ensemble_integration.py` (ensemble coordinator),
  `app/evidence_service.py` (canonical evidence builder),
  `app/image/forensics.py` / `app/image/metadata.py` / `app/image/ocr.py` /
  `app/image/qr.py`.

### K. Deployment / Delivery Diagram
```
GitHub Actions (deploy-pages.yml)
  │  npm ci (basirah)
  │  VITE_APP_MODE=showcase  (NO VITE_API_BASE_URL)
  │  npm run build
  │  configure-pages → upload-pages-artifact → deploy-pages
  ▼
GitHub Pages (static SPA)
  https://ish3-is.github.io/Aljuri/

Local development
  Frontend: Vite dev on http://127.0.0.1:5199 (proxy /api → :8000)
  Backend:  uvicorn app.main:app --host 127.0.0.1 --port 8000
  Runtime models (Git LFS):
    backend/models/basirah-url-v3.joblib
    backend/models/detector_b_clip_probe.joblib
    backend/models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt

Local demonstration
  cd basirah && npm run dev   (port 5199)
  backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  open http://127.0.0.1:5199
```

---

## 6. Result Inventory (Final Verified Evidence)

| Evidence | Status |
|---|---|
| URL model `basirah-url-v3` | PROMOTED (production pointer); advisory verdict, abstention |
| URL model evaluation | holdout + generalization artifacts in `backend/results/` |
| Cross-corpus limitation | survey/report artifacts (`backend/results/phaseX`) |
| Image detector (Detector A EfficientNet + Detector B CLIP probe) | RESEARCH result, ensemble evaluated; no detector met production criteria |
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

## 7. README Improvements (finalization)

The root `README.md` is being finalized with the following sections:
- Short project description
- **Live Showcase** (`https://ish3-is.github.io/Aljuri/`) — clearly states
  Showcase Mode only
- **Full Local Mode** — real analysis requires local backend
- Core Capabilities
- System Architecture (dual-mode diagram)
- Research Status
- Model Transparency
- Screenshots
- Run Locally
- Project Team (no student IDs exposed)
- Academic Notice
- Limitations
- Repository Structure

---

## 8. Screenshots Status

Target `docs/images/` (not yet present — create it):
- `home.png` — landing/dashboard
- `analyze.png` — analysis workspace
- `result.png` — evidence result
- `evidence-graph.png` — evidence graph
- `timeline.png` — analysis timeline
- `arabic-rtl.png` — Arabic/RTL render
- `dashboard.png` — dashboard/home

Rule applied before any screenshot is reused: no desktop clutter, no raw
dataset samples, no debug panels, no console errors, no private local paths.

---

## 9. Presentation Outline (22 slides)

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

## 10. Committee Q&A Bank (count = 18)

1. **Why not claim 99% accuracy?** — No evaluated detector met production
   criteria; claims are advisory with explicit uncertainty band, never a
   certification.
2. **Why does cross-corpus performance degrade?** — corpora are not drawn from
   the same domain distribution; coverage/abstention is raised when
   out-of-domain.
3. **Why is Detector B shadow-only?** — evaluated results did not meet the
   production deployment criteria; it is an ensemble research member only.
4. **Why no cloud backend?** — local-first for the defense/advisory use case
   and to keep the static GitHub Pages build free of live-inference logic.
5. **Why GitHub Pages only for showcase?** — Pages serves a static sample;
   real inference is deliberately local.
6. **How is BASIRAH different from VirusTotal?** — BASIRAH is an academic
   advisory evidence pipeline (URL + image + provenance + OCR/QR + fusion +
   graph/timeline) with explicit abstention and no enforcement.
7. **How do you prevent false claims of authenticity?** — the system never
   claims authenticity; it reports provenance state and advisory confidence.
8. **What happens if C2PA signature is invalid?** — provenance reports the
   invalid/untrusted state and the advisory verdict reflects it; no
   authenticity claim is made.
9. **Why use evidence fusion?** — single-modality numbers are fragile; fusion
   gives a defensible evidence basis and explicit abstention when coverage is
   low.
10. **What is the role of abstention?** — refuse to fabricate when uncertainty
    is high; the system says "uncertain" rather than overclaiming.
11. **How do you handle false positives?** — advisory framing, user-review
    workflow, and uncertainty band; no automated blocking.
12. **What are the ethical limitations?** — no legal/certified authenticity
    claim; advisory only; datasets licensed/excluded; research-grade images.
13. **How would you productionize it later?** — train/tune on a real
    labelled corpus (pending acquisition), formal validation against the
    deployment criteria, and (optionally) a cloud gateway with the same
    abstention discipline.
14. **Why was v1 retired and v3 selected?** — v3 passed holdout and
    generalization evaluation and is the pointer in `ACTIVE_MODEL.json`.
15. **What happens if the model is absent?** — heuristic engine carries the
    assessment; response reports `model_available = false`; no fabricated
    probability.
16. **Why a three-way verdict instead of binary?** — binary real/fake overclaims
    on synthetic-media/URL evidence; the uncertainty band is the scientific
    position.
17. **How is provenance verified?** — C2PA 0.38.0 preserving `status`,
    `manifest`, `sig`; validity is reported, not inferred from absence.
18. **What is the role of OCR/QR?** — forensic/content signals aggregated into
    evidence; they decode text/QR, they do not certify the media.

---

## 11. Demo Script (5–7 minutes)

1. Open BASIRAH locally (browser on `http://127.0.0.1:5199`).
2. Show dashboard/home.
3. Analyze suspicious URL → show URL evidence + advisory verdict.
4. Analyze image → show canonical verdict.
5. Show provenance (C2PA).
6. Show OCR/QR if applicable.
7. Show Evidence Graph.
8. Show Timeline.
9. Show report.
10. Switch Arabic/English (RTL).
11. Briefly show GitHub Pages showcase (`#/analyze` static sample).

**Fallback plan if live analysis fails**: the UI degrades to heuristic-only
assessment with `model_available = false`; the demo still demonstrates the
evidence view, provenance, graph/timeline, and report, and the README
documents the local-backend requirement.

---

## 12. Demo Safety

Never use: fake real-time result, unverified claim, "100% authentic",
"100% AI-generated".

Use: **Likely synthetic**, **Uncertain**, **Advisory**, **Caution**,
**No synthetic indicators detected**.
