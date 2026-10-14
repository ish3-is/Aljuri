# BASIRAH — Requirements Evidence (Internal Drafting Reference)

> Purpose: derive functional and non-functional requirements ONLY from
> implemented capabilities. Do not fabricate requirements the system does not
> meet.

---

## 1. Functional Requirements (from implemented capabilities)

| # | Requirement | Status |
|---|---|---|
| FR-1 | Analyze supported images (image/screenshot upload) | **VERIFIED** |
| FR-2 | Analyze suspicious URLs | **VERIFIED** |
| FR-3 | Inspect provenance (C2PA status/manifest/sig) | **VERIFIED** |
| FR-4 | Perform OCR (forensic signal) | **VERIFIED** |
| FR-5 | Detect QR (content signal) | **VERIFIED** |
| FR-6 | Inspect metadata | **VERIFIED** |
| FR-7 | Show forensic signals | **VERIFIED** |
| FR-8 | Correlate evidence | **VERIFIED** |
| FR-9 | Show evidence graph | **VERIFIED** |
| FR-10 | Show analysis timeline | **VERIFIED** |
| FR-11 | Generate evidence-oriented assessment (advisory) | **VERIFIED** |
| FR-12 | Support Arabic (RTL) and English | **VERIFIED** |

---

## 2. Non-Functional Requirements (from real implementation)

| # | Requirement | Status |
|---|---|---|
| NFR-1 | Explainability (evidence view shows why) | **VERIFIED** |
| NFR-2 | Scientific honesty (no overclaim, no fabricated results) | **VERIFIED** |
| NFR-3 | Accessibility (visible keyboard focus, no global outline removal) | **VERIFIED** |
| NFR-4 | Responsiveness (mobile/global + desktop, EN + AR RTL) | **VERIFIED** |
| NFR-5 | Read-only file analysis | **VERIFIED** |
| NFR-6 | No automatic browsing of submitted URLs | **VERIFIED** |
| NFR-7 | No execution of uploaded files | **VERIFIED** |
| NFR-8 | Deterministic traceability where applicable | **VERIFIED** |
| NFR-9 | Zero fabricated results (no invented benchmarks) | **VERIFIED** |

---

## 3. Explicitly Not Requirements (and must stay that way)

These are **NOT** requirements of BASIRAH, and the report must not claim
them:

- Not a legal / certified / official forensic certificate.
- Not a production-grade, legally-defensible image-authenticity service.
- No automatic URL browsing.
- No file execution.
