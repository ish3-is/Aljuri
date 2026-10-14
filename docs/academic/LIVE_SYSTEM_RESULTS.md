# BASIRAH — Live System Results (Internal Drafting Reference)

> Purpose: document actual verified system behavior. Separate **offline
> benchmark results** from **live system demonstration results**.

---

## 1. Real Frontend → Backend Evidence Flow

The verified production path is:

1. User uploads an image in the frontend (`EvidenceResultView`).
2. Frontend triggers the analysis; the file is sent to
   `POST /api/analyze/evidence?mode=auto`.
3. Backend returns the full canonical evidence payload (real HTTP 200).
4. `EvidenceResultView` renders: final assessment, provenance, evidence,
   graph, timeline, coverage, metadata/forensics, traceability.
5. No mock responses are used in this verified path.

---

## 2. Canonical Semantics

- **Canonical verdict:** three-way (trusted / uncertain / adversarial),
  with an explicit uncertainty band.
- **Advisory image detector policy:** a separate layer from the canonical
  verdict; the two do not coincide.
- **Provenance:** C2PA state preserved scientifically (`status`, `manifest`,
  `sig`).
- **Traceability:** real IDs only, clean traceability.

---

## 3. Evidence View (`EvidenceResultView`)

| Section | Verified |
|---|---|
| Final assessment | **VERIFIED** |
| Provenance | **VERIFIED** |
| Evidence | **VERIFIED** |
| Graph | **VERIFIED** (evidence graph rendered) |
| Timeline | **VERIFIED** (`timeline.ready === true`) |
| Coverage | **VERIFIED** (`coverage.detectorB`, `coverageSection`) |
| Metadata / forensics | **VERIFIED** |
| Traceability | **VERIFIED** |

---

## 4. Browser Verification Results

- Mobile 390×844: EN and AR RTL — `scrollWidth <= innerWidth` (long hashes
  wrap, ticker track caps, drift glows constrained).
- Desktop 1440×1000: EN and AR RTL — no regression.
- Keyboard-only focus: `a:focus-visible` visible, non-color-only.

---

## 5. Offline Benchmark Results (Live vs. Offline)

| Category | Status |
|---|---|
| Offline benchmark (Detector A/B, UnivFD candidate, holdout) | **VERIFIED** (in results/phase37) |
| Live demonstration (real image → evidence view) | **VERIFIED** (200 + evidence rendered) |
| Mobile/desktop responsive | **VERIFIED** |
| Accessibility | **VERIFIED** |

> Boundary rule: benchmark numbers and detector evaluations must be cited
> from `backend/results/phase37/` artifacts. They are **not** to be presented
> as production throughput or as a solved image-detection service.
