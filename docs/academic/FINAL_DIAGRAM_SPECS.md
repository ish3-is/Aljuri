# BASIRAH — FINAL DIAGRAM SPECIFICATIONS

> Implementation-accurate specs for the final report / presentation diagrams.
> No relational database is asserted — BASIRAH is stateless, in-memory,
> in-memory evidence store. The alternative logical model below replaces any
> ERD.

---

## A. System Architecture

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

---

## B. Use Case Diagram

Actor: **User**. Primary use cases:
1. Submit URL → get URL evidence + advisory verdict
2. Analyze image → evidence view (canonical verdict, provenance, forensics)
3. Show provenance → C2PA status/manifest/sig
4. Inspect OCR signal → OCR text
5. Inspect QR signal → decoded destination
6. View evidence graph → evidence graph (SVG)
7. View analysis timeline → stage timeline
8. Select language → EN / AR (RTL)
9. View sample result → static showcase result (GitHub Pages only)

---

## C. DFD Level 0 (context)

- **External agent**: User
- **Processes**:
  - URL intake → evidence pipeline → URL analysis
  - Image intake → evidence pipeline → image analysis
  - Output → evidence/UI/report
- **Data stores**:
  - evidence store (in-memory / transient)
  - model store (runtime models)
  - format schema store
- **Note**: NO persistent relational database exists in the system.

---

## D. DFD Level 1

Top-level decomposition of the evidence pipeline:
1. **Intake normalizer**: normalize URL; load image URL; read uploaded file
2. **Feature extractor**: URL features; file features (metadata, OCR, QR, forensics)
3. **Detectors**: Detector A (EfficientNet), Detector B (CLIP linear probe,
   shadow-only), UnivFD (research candidate, not promoted)
4. **URL model**: `basirah-url-v3` advisory distribution; abstention state
5. **Evidence fusion**: canonical aggregation, coverage, abstention accounting
6. **Output renderer**: EvidenceResultView (final assessment, provenance, graph,
   timeline, coverage, metadata/forensics, traceability, report)

---

## E. Sequence Diagram — Image Analysis

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

---

## F. Sequence Diagram — URL Analysis

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

---

## G. Sequence Diagram — Showcase Mode

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

---

## H. Evidence Fusion Flow

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

---

## I. Evidence Graph Flow

```
Evidence payload
  → nodes: signal sources (URL, image, provenance, OCR, QR, detectors)
  → edges: correlations (metadata↔OCR, QR↔destination, detector outputs, URL)
  → render EvidenceGraphView (SVG) + timeline + coverage
  → traceability IDs preserved
```

---

## J. Component/Class Diagram

- **URL architecture**:
  - `app/api/routes.py` (`PUT /api/analyze/evidence`)
  - `app/services/url_analyzer.py` (normalization, feature extraction, model interface)
  - `app/ml/production.py` (`ProductionModel`, `load_production_model`)
  - `app/ml/model_loader.py` (`ModelBundle`, `ModelStatus`)
- **Image architecture**:
  - `app/image/ensemble/detector_a.py` (EfficientNet)
  - `app/image/ensemble/detector_b.py` (CLIP linear probe, shadow-only)
  - `app/image/ensemble_integration.py` (ensemble coordinator)
  - `app/evidence_service.py` (canonical evidence builder)
  - `app/image/forensics.py` / `app/image/metadata.py` / `app/image/ocr.py` /
    `app/image/qr.py`

---

## K. Deployment / Delivery Diagram

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

## L. ERD Status

**Not applicable.** BASIRAH has no persistent relational database; no SQL
database exists. It is a stateless two-tier web application with an
in-memory/transient evidence store. The report should state:
"An ERD is not applicable to the deployed architecture. The logical model is
a component/evidence-flow diagram (above), with the runtime model bundle
(`backend/models/basirah-url-v3.joblib`) and the feature-schema contract as
the only durable artifacts."
