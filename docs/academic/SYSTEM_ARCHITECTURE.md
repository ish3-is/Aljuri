# BASIRAH — System Architecture (Internal Drafting Reference)

> Purpose: a factual system architecture reference for later academic
> chapters. This is **NOT** final university text. It preserves the verified
> implementation structure only.

---

## 1. Architectural Overview

BASIRAH is a **two-tier web application** (frontend + backend), with a
stateless evidence-analysis pipeline and an offline evaluation layer. The
frontend is a React 19 SPA; the backend is a FastAPI service.

**Frontend → Backend contract:** The Vite dev server (port 5199) proxies
`/api` to the backend (port 8000). At build time the frontend is a static
SPA; the backend remains a separate Python process.

---

## 2. Frontend Architecture

```
basirah/
  index.html
  src/
    main.tsx          # app entry
    features/
      result/
        EvidenceResultView.tsx    # the evidence view
    components/
      motion/                  # IntelligenceTicker (marquee)
      layout/                  # header / ticker layout
    styles/
      index.css                 # tokens, keyframes, mobile fixes
  public/            # static assets (logo etc.)
  docs/
    EVIDENCE_MODEL.md
    STAGE3_ARCHITECTURE_AUDIT.md
```

**Key frontend scripts** (from `package.json`):

| Script | Purpose |
|---|---|
| `dev` | Vite dev server on port 5199 |
| `build` | `tsc -b && vite build` → `dist/` |
| `lint` | eslint |
| `verify:wording` | `node scripts/verify-wording.mjs` |
| `verify:ui` | `node scripts/verify-ui.mjs` |
| `qa:p37` | `node qa/qa-p37.cjs` |

---

## 3. Backend Architecture

```
backend/
  app/
    main.py
    api/          # API modules
    core/         # config / exceptions
    content_intel.py
    evidence_service.py
    file_intel.py
    image/
    ml/
    schemas/
    services/
  app.main:app
```

**Production API:** `uvicorn app.main:app --host 127.0.0.1 --port 8000`

---

## 4. Data Flow — Live Analysis

```
User uploads image (file input)
  → frontend EvidenceResultView
  → /api/analyze/evidence (POST, mode=auto)
    → backend: canonical evidence pipeline
      → features (OCR / QR / metadata / forensics / C2PA provenance)
      → detector ensemble (Detector A + Detector B)
      → URL-model advisory distribution (URL analysis)
      → coverage / abstention accounting
      → canonical verdict, provenance state, traceability IDs
    → JSON evidence response
      → EvidenceResultView renders: final assessment, provenance, evidence,
        graph, timeline, coverage, metadata/forensics, traceability
```

---

## 5. Evidence Model (Key Entities)

- **Evidence** — the aggregated analysis result object (canonical verdict,
  advisory confidence, provenance state, coverage, traceability).
- **Provenance** — C2PA state (`status`, `manifest`, `sig`).
- **Traceability** — `findingCount`, `traceabilityCount`, `ids[]` (real IDs
  only; not fabricated).
- **Graph** — evidence graph; rendered in `EvidenceResultView`.
- **Timeline** — analysis timeline; `timeline.ready === true` asserted in QA.
- **Coverage** — `detectorB` score and `coverageSection` rendered in the view.

No persistent relational database is used; see the ERD decision below.

---

## 6. ERD Decision

**ERD: NOT APPLICABLE.** BASIRAH is a stateless evidence-analysis service.
It writes no persistent relational data model; uploaded files are analyzed
and not stored on disk as assets. Any schema diagrams must be marked
"not applicable / limited" rather than fabricated.

---

## 7. Diagrams to Prepare (Stage 4B)

| Diagram | Source of truth | Status |
|---|---|---|
| System Architecture Diagram | this file + vite.config.ts, app/ | ready |
| Use Case Diagram | requirements + result flow | draft (placeholder) |
| DFD | frontend→backend→evidence pipeline | draft (placeholder) |
| ERD | NOT APPLICABLE (no persistent relational model) | excluded |
| Sequence Diagram: Image Analysis | evidence service flow | draft |
| Sequence Diagram: URL Analysis | URL model pipeline | draft |
| Sequence Diagram: Evidence Correlation | evidence graph | draft |
| Class/Component Diagram | component/service map | draft |

---

## 8. Deployment Architecture

| Concern | Frontend | Backend |
|---|---|---|
| Artifact | `dist/` (static) | `uvicorn app.main:app` |
| Hosting | Static hosting / GitHub Pages (project site, `base: './'`) | Python-capable host |
| Load | Static browser + Vite dev proxy during dev | Reverse proxy / WAF |
| CORS | proxied; `changeOrigin: true`, `secure: false` | must allow `http://127.0.0.1:5199` |

**Known deployment constraint:** GitHub Pages serves static assets only and
can host the frontend, but **cannot** host FastAPI. A separate backend host
is required (see deployment-readiness report).
