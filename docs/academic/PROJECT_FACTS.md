# BASIRAH — Project Facts (Internal Drafting Reference)

> Purpose: a structured internal evidence pack. This is **NOT** the final
> university report. It contains only facts supported by the implemented
> BASIRAH project. Where a claim is not yet implemented, it is marked as a
> deferred capability.

---

## 1. Project Purpose

BASIRAH is a multimodal intelligence / defense advisory system that analyzes
**images**, **URLs**, and **screenshots** and produces an evidence-oriented
**advisory assessment** — never a legal or certified authenticity verdict.

Key principle, stated in the codebase: the system is **advisory**. It must
**not** claim "University certified", "Official forensic certificate",
"Legally verified authenticity", or any equivalent.

---

## 2. Supported Evidence Types

| Type | Evidence produced | Status |
|---|---|---|
| Image / screenshot | forensic signals, metadata, C2PA provenance, content heuristics | **VERIFIED IMPLEMENTATION** |
| URL | URL structural features, URL model distribution, advisory verdict | **VERIFIED IMPLEMENTATION** |
| Screenshot | full-page screenshot + evidence view | **VERIFIED IMPLEMENTATION** |

Supported image formats are whatever the evidence service decodes;
PNG/JPEG are the production fixtures.

---

## 3. Frontend Architecture

- **Framework**: React 19 (functional components, no class components)
- **UI**: Tailwind CSS 4 via `@tailwindcss/vite`; `clsx` utility; Lucide
  React icon set; `motion` (Framer Motion) for page transitions/animation
- **Build**: Vite 8 with `@vitejs/plugin-react`; `base: './'`
- **Dev server**: port 5199 (`strictPort: true`)
- **API proxy**: `/api` → `http://127.0.0.1:8000` (`changeOrigin: true`,
  `secure: false`), defined in `vite.config.ts`
- **Static export**: `vite build` → `dist/` (deployable as static assets)

Main result-view component: `src/features/result/EvidenceResultView.tsx`.

---

## 4. Backend Architecture

- **Framework**: FastAPI 0.115.6 with Uvicorn
- **Validation**: Pydantic v2 (`pydantic==2.10.4`, `pydantic-settings==2.7.0`)
- **URL parsing**: `tldextract==5.1.2`
- **ML/eval**: `scikit-learn==1.6.1`, `joblib==1.4.2`, `xgboost==3.4.1`,
  `matplotlib==3.11.2`
- **Provenance**: `c2pa-python==0.38.0` (C2PA 0.38.0)
- **App entry**: `app/main.py` → `app.main:app`

Structure:

```
app/
  main.py
  api/          # API route modules
  core/         # shared core (config, exceptions, etc.)
  content_intel.py      # content intelligence utilities
  evidence_service.py   # canonical evidence aggregation
  evidence/         # evidence-building packages
  file_intel.py         # file-intelligence utilities
  image/            # image handling
  ml/               # ML models + evaluation
  schemas/          # Pydantic request/response schemas
  services/         # service layer
```

---

## 5. Real API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /api/health` | GET | Service health check |
| `POST /api/analyze/evidence` | POST | Run real analysis (upload image → canonical evidence) |

The `/api/analyze/evidence` endpoint accepts `mode=auto` (production analysis)
and returns the full evidence payload: canonical verdict, provenance, evidence,
graph, timeline, coverage, traceability, metadata/forensics.

---

## 6. Image Research Status

- Research-grade detectors evaluated: **Detector A** and **Detector B**
  (the two production detectors), plus a **UnivFD candidate** where applicable.
- **Status: research-grade, advisory-only.** No evaluated detector met the
  production deployment criteria.
- The project does **NOT** present image AI detection as solved.

---

## 7. URL Research Status

- URL analysis builds structural features and produces a model distribution
  and advisory verdict.
- **Research / evaluation work**: train URL model, holdout evaluation,
  URL model security scoring.
- **Status: verified implementation for the supported URL pipeline.**

---

## 8. C2PA Behavior

- `c2pa-python==0.38.0` is a **production dependency**.
- Provenance state is preserved scientifically:
  `provenance.status`, `provenance.manifest`, `provenance.sig`.
- The evidence service reports C2PA status/manifest/signature where present.

---

## 9. OCR

- PaddleOCR integration exists for OCR evaluation (multi-language).
- OCR is used as a **forensic/heuristic signal**, not as a verdict source.
- MNIST and other digit-recognition models were used to verify OCR correctness
  of the classifier pipeline (e.g. distinguishing real '8' vs. fooling OCR).

---

## 10. QR

- QR-code detection works via a QR execution engine (PDF417-compatible engine
  evaluated; tesseract OCR verified as a fallback).
- QR is a content signal; it does not independently change the verdict.

---

## 11. Metadata / Forensics

- **Metadata**: stored/inspected as part of evidence; presented under
  "metadata" in the evidence view. Long hashes/URLs wrap on mobile via
  `overflow-wrap`.
- **Forensics**: extracted/rendered as part of evidence; presented as a
  forensic signals section.
- `file_intel`, `metadata` integration, and `/api/analyze/evidence` are the
  verified production surface.

---

## 12. Evidence Graph

- The evidence graph is rendered in `EvidenceResultView` (plots the graph
  canvas).
- Graph semantics are an executed feature, not a stub.

---

## 13. Timeline

- The analysis timeline is rendered in `EvidenceResultView`.
- `timeline.ready === true` is asserted by frontend verification tests.

---

## 14. Coverage

- `coverage.detectorB` (production coverage score) and
  `coverage.coverageSection` are reported by the evidence service and
  rendered by `EvidenceResultView`.
- Coverage is computed in the evidence service; the frontend consumes it.

---

## 15. Traceability

- `traceability.findingCount`, `traceability.traceabilityCount`, and
  `traceability.ids` are produced by the backend, returned by the analysis
  API, rendered in the evidence view, and asserted by frontend verification
  tests.
- Verified: clean traceability, non-empty `ids` when applicable.

---

## 16. Languages

- **EN (English)** and **AR (Arabic, RTL)**.
- Arabic RTL verified in browser QA (mobile 390×844 and desktop 1440×1000).

---

## 17. Deployment Constraints

- **Frontend**: static assets (`dist/`), Vite `base: './'` for project-site
  deployment.
- **Backend**: Python-capable host required (FastAPI/uvicorn).
- **GitHub Pages cannot host FastAPI** (static only) — see the deployment
  readiness report in this pack.

---

## 18. Scientific Limitations

- Image AI detection is **advisory/research-grade**. It is not a
  production-grade, legally-defensible authentication service.
- The system does **not** automatically browse submitted URLs and does not
  execute uploaded file content.
- The design is a **no-fabrication** system: deferred capabilities are
  documented, never implied as shipped.

---

## 19. Verified vs. Deferred Legend

| Tag | Meaning |
|---|---|
| **VERIFIED IMPLEMENTATION** | Shipped and tested in this repository |
| **RESEARCH RESULT** | Experimental finding, not yet production-released |
| **LIMITATION** | Documented scientific or engineering constraint |
| **DEFERRED CAPABILITY** | Planned but not yet implemented |

---
