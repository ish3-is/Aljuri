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

## Key capabilities

| Evidence stream | What it does |
|---|---|
| **Visual / provenance** | C2PA 0.38.0 signature verification, metadata extraction, OCR / QR decoding, forensic image analysis |
| **URL intelligence** | Normalisation, reputation scoring, risk banding, trust scoring |
| **Detection** | Machine-learning detectors (Detector A / Detector B) with honest unavailability |
| **Evidence graph** | Structured graph of sourced findings with real traceability IDs |
| **Evidence coverage** | Per-evidence-type coverage heatmap |
| **Analysis timeline** | Chronological, traceable reconstruction of each analysis |

## Supported evidence types

- Images and screenshots (with provenance)
- URLs (parsed, never opened — no fetching, no JS, no external calls)
- Uploaded files (hardened sanitisation; no execution)

## System architecture

```
basirah/                # Frontend (React + TypeScript + Vite)
backend/                # Backend (FastAPI)
  app/
    main.py             # FastAPI app, CORS
    api/                # Routes
    core/               # Config, thresholds, validation
    services/           # URL analyzer, feature extractor, heuristic engine,
                        #   risk engine, explanation engine, analyzer
    ml/                 # Model loading, predictor, dataset
  datasets/             # Dev fixture + dataset documentation
  scripts/              # Training / evaluation entry points
  tests/                # pytest suite
```

## Technology stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Playwright (QA)
- **Backend:** FastAPI, Uvicorn, Pydantic v2
- **Provenance:** C2PA (c2pa-python 0.38.0)
- **OCR / QR:** pytesseract + Pillow; QR decode via `pyzbar` / `opencv-python-headless`
- **ML:** scikit-learn, joblib
- **PDF / spreadsheets:** openpyxl, reportlab, xlsxwriter
- **Testing:** pytest, Playwright

## Scientific positioning

BASIRAH is an **advisory / research-grade** system, not a forensic
certifier. It:

- is **not** "99% accurate" or "detects all AI images" — no such claim is
  supported by the current evidence;
- does **not** guarantee authenticity;
- does **not** produce forensic-certified or university-certified results;
- abstains when evidence is conflicting or insufficient;
- treats a "no synthetic indicators" outcome as **insufficient evidence of
  authenticity**, not proof of authenticity.

See the **Limitations** section below for the full, honest statement.

## Local setup

### Prerequisites

- Python 3.12+ (developed on 3.12.1)
- Node.js 20+ (Windows native)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend serves on `http://127.0.0.1:8000` (health at
`/api/health`).

### Frontend

```powershell
cd basirah
npm ci
copy .env.example .env.local
npm run dev
```

The dev server runs on port **5199** (Vite dev server on
`http://127.0.0.1:5199`). API calls are proxied to the backend at
`http://127.0.0.1:8000` via the Vite proxy (`/api`).

### Environment variables

See `.env.example` (frontend). The production example uses the same-origin
setting; set `VITE_API_BASE_URL` during local development to reach the
backend.

## Testing

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest tests\ -q

# Frontend
cd basirah
npx tsc -p tsconfig.app.json --noEmit   # type check
npm run lint                              # ESLint
npm run build                             # production build
node scripts/verify-wording.mjs           # wording checks
node scripts/verify-ui.mjs                # UI checks
```

## Limitations (read before use)

1. **Advisory, not forensic.** Detection of synthetic imagery is
   research-grade. Do not rely on it as sole evidence of authenticity or
   fabrication.
2. **No URL browsing.** Submitted URLs are parsed and scored, never opened
   or dereferenced. JavaScript and external resources are never executed.
3. **No file execution.** Uploaded files are sanitized and inspected, never
   executed.
4. **Advisory models.** BASIRAH ships three runtime ML models via Git LFS:
   `backend/models/basirah-url-v3.joblib`,
   `backend/models/detector_b_clip_probe.joblib`, and
   `backend/models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt`.
   Small metadata files (ACTIVE_MODEL.json, RESEARCH_IMAGE_MODEL.json,
   feature_schema.json) are tracked as normal Git text. No
   model-performance claims are made.
5. **C2PA is data-dependent.** Missing or malformed provenance manifests
   yield `unavailable`, not a verdict.
6. **Local-only at this stage.** No automatic URL browsing; no persistent
   cloud storage; model packaging excluded from this repository.
 BASIRAH | بصيرة

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

## Key capabilities

| Evidence stream | What it does |
|---|---|
| **Visual / provenance** | C2PA 0.38.0 signature verification, metadata extraction, OCR / QR decoding, forensic image analysis |
| **URL intelligence** | Normalisation, reputation scoring, risk banding, trust scoring |
| **Detection** | Machine-learning detectors (Detector A / Detector B) with honest unavailability |
| **Evidence graph** | Structured graph of sourced findings with real traceability IDs |
| **Evidence coverage** | Per-evidence-type coverage heatmap |
| **Analysis timeline** | Chronological, traceable reconstruction of each analysis |

## Supported evidence types

- Images and screenshots (with provenance)
- URLs (parsed, never opened — no fetching, no JS, no external calls)
- Uploaded files (hardened sanitisation; no execution)

## System architecture

```
basirah/                # Frontend (React + TypeScript + Vite)
backend/                # Backend (FastAPI)
  app/
    main.py             # FastAPI app, CORS
    api/                # Routes
    core/               # Config, thresholds, validation
    services/           # URL analyzer, feature extractor, heuristic engine,
                        #   risk engine, explanation engine, analyzer
    ml/                 # Model loading, predictor, dataset
  datasets/             # Dev fixture + dataset documentation
  scripts/              # Training / evaluation entry points
  tests/                # pytest suite
```

## Technology stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Playwright (QA)
- **Backend:** FastAPI, Uvicorn, Pydantic v2
- **Provenance:** C2PA (c2pa-python 0.38.0)
- **OCR / QR:** pytesseract + Pillow; QR decode via `pyzbar` / `opencv-python-headless`
- **ML:** scikit-learn, joblib
- **PDF / spreadsheets:** openpyxl, reportlab, xlsxwriter
- **Testing:** pytest, Playwright

## Scientific positioning

BASIRAH is an **advisory / research-grade** system, not a forensic
certifier. It:

- is **not** "99% accurate" or "detects all AI images" — no such claim is
  supported by the current evidence;
- does **not** guarantee authenticity;
- does **not** produce forensic-certified or university-certified results;
- abstains when evidence is conflicting or insufficient;
- treats a "no synthetic indicators" outcome as **insufficient evidence of
  authenticity**, not proof of authenticity.

See the **Limitations** section below for the full, honest statement.

## Local setup

### Prerequisites

- Python 3.12+ (developed on 3.12.1)
- Node.js 20+ (Windows native)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend serves on `http://127.0.0.1:8000` (health at
`/api/health`).

### Frontend

```powershell
cd basirah
npm ci
copy .env.example .env.local
npm run dev
```

The dev server runs on port **5199** (Vite dev server on
`http://127.0.0.1:5199`). API calls are proxied to the backend at
`http://127.0.0.1:8000` via the Vite proxy (`/api`).

### Environment variables

See `.env.example` (frontend). The production example uses the same-origin
setting; set `VITE_API_BASE_URL` during local development to reach the
backend.

## Testing

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest tests\ -q

# Frontend
cd basirah
npx tsc -p tsconfig.app.json --noEmit   # type check
npm run lint                              # ESLint
npm run build                             # production build
node scripts/verify-wording.mjs           # wording checks
node scripts/verify-ui.mjs                # UI checks
```

## Limitations (read before use)

1. **Advisory, not forensic.** Detection of synthetic imagery is
   research-grade. Do not rely on it as sole evidence of authenticity or
   fabrication.
2. **No URL browsing.** Submitted URLs are parsed and scored, never opened
   or dereferenced. JavaScript and external resources are never executed.
3. **No file execution.** Uploaded files are sanitized and inspected, never
   executed.
4. **Advisory models.** BASIRAH ships three runtime ML models via Git LFS:
   `backend/models/basirah-url-v3.joblib`,
   `backend/models/detector_b_clip_probe.joblib`, and
   `backend/models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt`.
   Small metadata files (ACTIVE_MODEL.json, RESEARCH_IMAGE_MODEL.json,
   feature_schema.json) are tracked as normal Git text. No
   model-performance claims are made.
5. **C2PA is data-dependent.** Missing or malformed provenance manifests
   yield `unavailable`, not a verdict.
6. **Local-only at this stage.** No automatic URL browsing; no persistent
   cloud storage; model packaging excluded from this repository.
 BASIRAH | بصيرة

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

## Key capabilities

| Evidence stream | What it does |
|---|---|
| **Visual / provenance** | C2PA 0.38.0 signature verification, metadata extraction, OCR / QR decoding, forensic image analysis |
| **URL intelligence** | Normalisation, reputation scoring, risk banding, trust scoring |
| **Detection** | Machine-learning detectors (Detector A / Detector B) with honest unavailability |
| **Evidence graph** | Structured graph of sourced findings with real traceability IDs |
| **Evidence coverage** | Per-evidence-type coverage heatmap |
| **Analysis timeline** | Chronological, traceable reconstruction of each analysis |

## Supported evidence types

- Images and screenshots (with provenance)
- URLs (parsed, never opened — no fetching, no JS, no external calls)
- Uploaded files (hardened sanitisation; no execution)

## System architecture

```
basirah/                # Frontend (React + TypeScript + Vite)
backend/                # Backend (FastAPI)
  app/
    main.py             # FastAPI app, CORS
    api/                # Routes
    core/               # Config, thresholds, validation
    services/           # URL analyzer, feature extractor, heuristic engine,
                        #   risk engine, explanation engine, analyzer
    ml/                 # Model loading, predictor, dataset
  datasets/             # Dev fixture + dataset documentation
  scripts/              # Training / evaluation entry points
  tests/                # pytest suite
```

## Technology stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Playwright (QA)
- **Backend:** FastAPI, Uvicorn, Pydantic v2
- **Provenance:** C2PA (c2pa-python 0.38.0)
- **OCR / QR:** pytesseract + Pillow; QR decode via `pyzbar` / `opencv-python-headless`
- **ML:** scikit-learn, joblib
- **PDF / spreadsheets:** openpyxl, reportlab, xlsxwriter
- **Testing:** pytest, Playwright

## Scientific positioning

BASIRAH is an **advisory / research-grade** system, not a forensic
certifier. It:

- is **not** "99% accurate" or "detects all AI images" — no such claim is
  supported by the current evidence;
- does **not** guarantee authenticity;
- does **not** produce forensic-certified or university-certified results;
- abstains when evidence is conflicting or insufficient;
- treats a "no synthetic indicators" outcome as **insufficient evidence of
  authenticity**, not proof of authenticity.

See the **Limitations** section below for the full, honest statement.

## Local setup

### Prerequisites

- Python 3.12+ (developed on 3.12.1)
- Node.js 20+ (Windows native)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend serves on `http://127.0.0.1:8000` (health at
`/api/health`).

### Frontend

```powershell
cd basirah
npm ci
copy .env.example .env.local
npm run dev
```

The dev server runs on port **5199** (Vite dev server on
`http://127.0.0.1:5199`). API calls are proxied to the backend at
`http://127.0.0.1:8000` via the Vite proxy (`/api`).

### Environment variables

See `.env.example` (frontend). The production example uses the same-origin
setting; set `VITE_API_BASE_URL` during local development to reach the
backend.

## Testing

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest tests\ -q

# Frontend
cd basirah
npx tsc -p tsconfig.app.json --noEmit   # type check
npm run lint                              # ESLint
npm run build                             # production build
node scripts/verify-wording.mjs           # wording checks
node scripts/verify-ui.mjs                # UI checks
```

## Limitations (read before use)

1. **Advisory, not forensic.** Detection of synthetic imagery is
   research-grade. Do not rely on it as sole evidence of authenticity or
   fabrication.
2. **No URL browsing.** Submitted URLs are parsed and scored, never opened
   or dereferenced. JavaScript and external resources are never executed.
3. **No file execution.** Uploaded files are sanitized and inspected, never
   executed.
4. **Advisory models.** BASIRAH ships three runtime ML models via Git LFS:
   `backend/models/basirah-url-v3.joblib`,
   `backend/models/detector_b_clip_probe.joblib`, and
   `backend/models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt`.
   Small metadata files (ACTIVE_MODEL.json, RESEARCH_IMAGE_MODEL.json,
   feature_schema.json) are tracked as normal Git text. No
   model-performance claims are made.
5. **C2PA is data-dependent.** Missing or malformed provenance manifests
   yield `unavailable`, not a verdict.
6. **Local-only at this stage.** No automatic URL browsing; no persistent
   cloud storage; model packaging excluded from this repository.
 BASIRAH | بصيرة

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

## Key capabilities

| Evidence stream | What it does |
|---|---|
| **Visual / provenance** | C2PA 0.38.0 signature verification, metadata extraction, OCR / QR decoding, forensic image analysis |
| **URL intelligence** | Normalisation, reputation scoring, risk banding, trust scoring |
| **Detection** | Machine-learning detectors (Detector A / Detector B) with honest unavailability |
| **Evidence graph** | Structured graph of sourced findings with real traceability IDs |
| **Evidence coverage** | Per-evidence-type coverage heatmap |
| **Analysis timeline** | Chronological, traceable reconstruction of each analysis |

## Supported evidence types

- Images and screenshots (with provenance)
- URLs (parsed, never opened — no fetching, no JS, no external calls)
- Uploaded files (hardened sanitisation; no execution)

## System architecture

```
basirah/                # Frontend (React + TypeScript + Vite)
backend/                # Backend (FastAPI)
  app/
    main.py             # FastAPI app, CORS
    api/                # Routes
    core/               # Config, thresholds, validation
    services/           # URL analyzer, feature extractor, heuristic engine,
                        #   risk engine, explanation engine, analyzer
    ml/                 # Model loading, predictor, dataset
  datasets/             # Dev fixture + dataset documentation
  scripts/              # Training / evaluation entry points
  tests/                # pytest suite
```

## Technology stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Playwright (QA)
- **Backend:** FastAPI, Uvicorn, Pydantic v2
- **Provenance:** C2PA (c2pa-python 0.38.0)
- **OCR / QR:** pytesseract + Pillow; QR decode via `pyzbar` / `opencv-python-headless`
- **ML:** scikit-learn, joblib
- **PDF / spreadsheets:** openpyxl, reportlab, xlsxwriter
- **Testing:** pytest, Playwright

## Scientific positioning

BASIRAH is an **advisory / research-grade** system, not a forensic
certifier. It:

- is **not** "99% accurate" or "detects all AI images" — no such claim is
  supported by the current evidence;
- does **not** guarantee authenticity;
- does **not** produce forensic-certified or university-certified results;
- abstains when evidence is conflicting or insufficient;
- treats a "no synthetic indicators" outcome as **insufficient evidence of
  authenticity**, not proof of authenticity.

See the **Limitations** section below for the full, honest statement.

## Local setup

### Prerequisites

- Python 3.12+ (developed on 3.12.1)
- Node.js 20+ (Windows native)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend serves on `http://127.0.0.1:8000` (health at
`/api/health`).

### Frontend

```powershell
cd basirah
npm ci
copy .env.example .env.local
npm run dev
```

The dev server runs on port **5199** (Vite dev server on
`http://127.0.0.1:5199`). API calls are proxied to the backend at
`http://127.0.0.1:8000` via the Vite proxy (`/api`).

### Environment variables

See `.env.example` (frontend). The production example uses the same-origin
setting; set `VITE_API_BASE_URL` during local development to reach the
backend.

## Testing

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m pytest tests\ -q

# Frontend
cd basirah
npx tsc -p tsconfig.app.json --noEmit   # type check
npm run lint                              # ESLint
npm run build                             # production build
node scripts/verify-wording.mjs           # wording checks
node scripts/verify-ui.mjs                # UI checks
```

## Limitations (read before use)

1. **Advisory, not forensic.** Detection of synthetic imagery is
   research-grade. Do not rely on it as sole evidence of authenticity or
   fabrication.
2. **No URL browsing.** Submitted URLs are parsed and scored, never opened
   or dereferenced. JavaScript and external resources are never executed.
3. **No file execution.** Uploaded files are sanitized and inspected, never
   executed.
4. **No trained model ships with this repository.** The training pipeline
   is complete and verified, but no real labelled dataset has been
   acquired, so no model is included and no evaluation metrics are claimed.
5. **Model evaluation is pending dataset acquisition.** Any reported
   accuracy is provisional and dataset-dependent.
6. **C2PA is data-dependent.** Missing or malformed provenance manifests
   yield `unavailable`, not a verdict.
7. **Local-only at this stage.** No automatic URL browsing; no persistent
   cloud storage; no model packaging.

## Repository structure

```
basirah/
  src/                      # Frontend source
  public/                   # Static assets
  scripts/                  # Frontend QA / verification tools
  package.json
  package-lock.json
  tsconfig*.json
  vite.config.ts
  eslint.config.js
  index.html

backend/
  app/                      # FastAPI application
  tests/                    # pytest suite
  datasets/                 # Dev fixture + documentation
  scripts/                  # Training / evaluation entry points
  requirements.txt

docs/
  academic/                 # Academic evidence pack (Stage 4)
  phase2-url-intelligence.md

LICENSE
README.md
.env.example
```

## Academic context

BASIRAH is developed as part of an academic research project. The
evidence pack (project facts, verification status, limitations, and
traceability) is published under `docs/academic/`.

> This is **not** the final university report. University formatting and
> chapters are blocked pending official university files.

## License

MIT (see `LICENSE`). See `LICENSE` for the full text.

## Status

- **Stage 2 — URL Intelligence:** COMPLETE
- **Stage 3 — Evidence Experience:** COMPLETE
- **Stage 4 Foundation — Academic Packaging:** COMPLETE

Publication to GitHub is **not yet initiated** (hidden behind a separate
explicit authorization).
