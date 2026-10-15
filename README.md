# BASIRAH | بصيرة

**Basirah** (Arabic for "foresight" / "discernment") is a multimodal
intelligence advisory system for synthetic-media, URL, and screenshot
analysis. It consolidates multiple independent evidence streams — visual
forensics (C2PA provenance, OCR, QR decoding, metadata), URL intelligence,
and machine-learning detection — and fuses them into a single transparent
trust assessment.

> **Scientific positioning.** BASIRAH does **not** claim perfect
> AI-image or synthetic-content detection. Image detection remains
> **advisory / research-grade**.
>
> The system:
> - correlates multiple independent evidence sources,
> - abstains when evidence is insufficient or conflicting,
> - does **not** equate "no synthetic indicators" with verified
>   authenticity,
> - does **not** automatically browse submitted URLs,
> - does **not** execute uploaded files.
>
> Any result must be read as a **decision-support signal**, not an
> authoritative verdict.

---

## Live Showcase

**URL:** `https://ish3-is.github.io/Aljuri/`

This is the **Showcase Mode only** deployment. It is built by the automated
workflow (`.github/workflows/deploy-pages.yml`) with `VITE_APP_MODE=showcase`
and **no** `VITE_API_BASE_URL`. It is deliberately **static and demo-only**:

- renders a banner + the static sample result (`View Sample Analysis`,
  labelled **DEMO — SAMPLE RESULT**),
- makes **no API calls**, runs **no ML inference**, performs **no live
  analysis**,
- produces **no HTTP 405** — any real-analysis attempt is blocked in
  frontend code.

> Do not claim the Pages build performs real model inference. The live
> showcase is a static preview; real analysis happens in **Full Local Mode**.

## Full Local Mode

**Real analysis requires the local backend.** Full Local Mode runs the real
FastAPI backend (`127.0.0.1:8000`) with the runtime models and produces the
real evidence pipeline: canonical verdict, evidence fusion, evidence graph,
timeline, provenance, OCR/QR, detector outputs, report generation.

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000

cd basirah
npm ci
copy .env.example .env.local
npm run dev
```

- Frontend: `http://127.0.0.1:5199` (Vite dev server, `/api` proxied to
  `http://127.0.0.1:8000`)
- Backend: live URL/image/evidence analysis, canonical verdict, evidence
  fusion, evidence graph, timeline, detector outputs, report generation
- Models (Git LFS): `backend/models/basirah-url-v3.joblib`,
  `backend/models/detector_b_clip_probe.joblib`, and the image model under
  `backend/models/multifamily_candidates/`

---

## Core Capabilities

| Evidence stream | What it does |
|---|---|
| **Visual / provenance** | C2PA 0.38.0 signature verification, metadata extraction, OCR / QR decoding, forensic image analysis |
| **URL intelligence** | Normalisation, reputation scoring, risk banding, trust scoring |
| **Detection** | Machine-learning detectors (Detector A / Detector B) with honest unavailability |
| **Evidence graph** | Structured graph of sourced findings with real traceability IDs |
| **Evidence coverage** | Per-evidence-type coverage heatmap |
| **Analysis timeline** | Chronological, traceable reconstruction of each analysis |

### Supported evidence types

- Images and screenshots (with provenance)
- URLs (parsed, never opened — no fetching, no JS, no external calls)
- Uploaded files (hardened sanitisation; no execution)

### Research status (advisory)

- **URL intelligence**: model-backed, verified implementation, advisory
- **Image intelligence**: research-grade, advisory only; no evaluated
  detector met the production deployment criteria
- **OCR**: Tesseract/EasyOCR fallback
- **QR**: OpenCV
- **Provenance (C2PA)**: verification of manifest/signature state
- **UnivFD**: evaluated only, not promoted
- **Detector B**: shadow-only (no enforcement)

---

## System Architecture

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

- URL analysis: `POST /api/analyze/evidence?mode=auto`
- Image analysis: `POST /api/analyze/evidence` (upload)
- Real analysis requires the local backend; the static GitHub Pages site is a
  safe, demo-only preview.

### Evidence flow

```
User submits URL or image
  → React/Vite front-end (UniversalInput)
  → POST /api/analyze/evidence (mode=auto)
    → features (metadata, OCR, QR, forensics, C2PA)
    → detector ensemble (A + B [shadow], UnivFD [research])
    → URL-model advisory distribution (v3)
    → coverage / abstention accounting
    → canonical verdict + provenance + evidence + graph + timeline
  → EvidenceResultView renders the full evidence view
```

---

## Research Status

- **URL model (`basirah-url-v3`)**: PROMOTED, production pointer (advisory).
  Evaluated on holdout + generalization corpora.
- **Image detectors (A EfficientNet, B CLIP linear probe)**: PRODUCTION
  entries, **advisory/research-grade**. No detector met the production
  deployment criteria.
- **UnivFD**: evaluated where applicable, NOT promoted.
- **Detector B**: shadow-only (no enforcement).
- **OCR / QR**: forensic/content signals, verified.
- **C2PA provenance**: verified, reported as status/manifest/sig.
- **Project type**: defense advisory demonstration, not a certified
  forensic/compliance tool.

### Model Transparency

| Component | Role | Production Status | Evaluation | Deployment Suitability | Limitation |
|---|---|---|---|---|---|
| URL Model v3 | Advisory URL verdict | PROMOTED | VERIFIED | Advisory only | Cross-domain limited; no 0.99 precision |
| Detector A (EfficientNet) | Image detector | Promoted (advisory) | RESEARCH | Advisory only | No detector met production criteria |
| Detector B (CLIP probe) | Shadow-only | Shadow-only | RESEARCH | Not deployable | Shadow member only |
| UnivFD | Research candidate | NOT PROMOTED | RESEARCH | Not production-suitable | Research candidate only |
| C2PA | Provenance verification | VERIFIED | VERIFIED | Verification only | Cannot claim authenticity from absence |
| OCR | Forensic signal | VERIFIED | RESEARCH | Advisory | Depends on resolution |
| QR | Content signal | VERIFIED | RESEARCH | Advisory | Decodes destination, does not verify page |

See `docs/academic/MODEL_TRUTH_TABLE.md` for the full table.

---

## Screenshots

Target `docs/images/`:

- `home.png` — landing / dashboard
- `analyze.png` — analysis workspace
- `result.png` — evidence result
- `evidence-graph.png` — evidence graph
- `timeline.png` — analysis timeline
- `arabic-rtl.png` — Arabic / RTL render
- `dashboard.png` — dashboard

Rule: no desktop clutter, no raw dataset samples, no debug panels, no console
errors, no private local paths.

---

## Run Locally

### Prerequisites

- Python 3.12+ (developed on 3.12.1)
- Node.js 20+ (Windows native)

### Backend

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health: `GET http://127.0.0.1:8000/api/health`

### Frontend

```powershell
cd basirah
npm ci
copy .env.example .env.local
npm run dev
```

Dev server: `http://127.0.0.1:5199`; API proxied to the backend.

### Tests

```powershell
# Backend
cd backend
.\\.venv\\Scripts\\Activate.ps1
python -m pytest tests\ -q

# Frontend
cd basirah
npx tsc -p tsconfig.app.json --noEmit
npm run lint
npm run build
node scripts/verify-wording.mjs
node scripts/verify-ui.mjs
```

---

## Project Team

Student project. See repository authorship in `git log` and `git shortlog`.

## Academic Notice

This is an **academic research project**. The evidence pack is published under
`docs/academic/`:

- `STAGE5_PACKAGE.md` — Stage 5 package
- `COMMITTEE_QA_BANK.md` — Committee Q&A
- `LIVE_DEMO_SCRIPT.md` — Live demo script
- `FINAL_RESULTS_INVENTORY.md` — Final verified results
- `FINAL_DIAGRAM_SPECS.md` — Final diagram specifications

> This is **not** the final university report. University formatting and
> chapters are blocked pending official university files. Supervisor and
> examiner names, semester, and year are placeholders.

## Limitations

1. **Advisory, not forensic.** Detection of synthetic imagery is
   research-grade. Do not rely on it as sole evidence of authenticity or
   fabrication.
2. **No URL browsing.** Submitted URLs are parsed and scored, never opened or
   dereferenced. JavaScript and external resources are never executed.
3. **No file execution.** Uploaded files are sanitized and inspected, never
   executed.
4. **Advisory models.** BASIRAH ships runtime ML models via Git LFS:
   `backend/models/basirah-url-v3.joblib`,
   `backend/models/detector_b_clip_probe.joblib`, and the image model under
   `backend/models/multifamily_candidates/`. No model-performance claims are
   made.
5. **C2PA is data-dependent.** Missing or malformed provenance manifests yield
   `unavailable`, not a verdict.
6. **Local-only at this stage.** No automatic URL browsing; no persistent cloud
   storage; model packaging excluded from this repository.
7. **Showcase is demo-only.** The static GitHub Pages site makes no real
   analysis; real work happens in Full Local Mode.

## Repository Structure

```
basirah/                # Frontend (React + TypeScript + Vite)
backend/                # Backend (FastAPI)
  app/                  # FastAPI application
    api/                # Routes
    core/               # Config, thresholds, validation
    services/           # URL analyzer, feature extractor, heuristic engine,
                        #   risk engine, explanation engine, analyzer
    ml/                 # Model loading, predictor, dataset
  datasets/             # Dev fixture + documentation
  scripts/              # Training / evaluation entry points
  tests/                # pytest suite
  requirements.txt
docs/                    # Project documentation
  academic/             # Academic evidence pack (Stage 4 / Stage 5)
  *.md                  # Other project docs
LICENSE
README.md
```

---

## Academic Context

BASIRAH is developed as part of an academic research project. The evidence pack
(project facts, verification status, limitations, and traceability) is under
`docs/academic/`.

> This is **not** the final university report. University formatting and
> chapters are blocked pending official university files. Supervisor and
> examiner names, semester, and year are placeholders.

---
