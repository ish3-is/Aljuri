# BASIRAH — PHASE 5 / STAGE 3 ARCHITECTURE AUDIT

## Project Layout

### Frontend: `D:\MDR\Aljuri-Greadute-Project\basirah`
- **src/features/result/** — EvidenceResultView, panels, hero, gauge, status row
- **src/features/analysis/** — evidenceProvider, imageProvider, providers, stageModel
- **src/features/universal-input/** — UniversalInput (input layer)
- **src/features/graph/** — EvidenceGraphView (graph)
- **src/features/investigation-timeline/** — InvestigationTimeline
- **src/features/reports/** — Report mappers, export, document view
- **src/features/trust-dna/** — TrustDNA
- **src/hooks/** — useInvestigation, useEnvironment, useSection, useTheme
- **src/types/analysis.ts** — domain types (the analysis contract)
- **src/i18n/translations.ts** — bilingual copy (660+ lines)
- **src/data/mockAnalysis.ts** — mock data

### Backend: `D:\MDR\Aljuri-Greadute-Project\backend`
- **app/evidence_service.py** — multimodal orchestrator
- **app/image/service.py** — image analysis service
- **app/image/forensics.py** — forensic signals
- **app/image/metadata.py** — EXIF extraction
- **app/image/provenance.py** — C2PA/Content Credentials
- **app/evidence/correlation.py** — evidence correlation & graph
- **app/evidence/coverage.py** — analyzer coverage
- **app/services/** — analyzer, feature_extractor, heuristic_engine, risk_engine, url_analyzer
- **app/schemas/** — requests.py, responses.py

## Key Architectural Findings

### Existing components currently responsible for evidence presentation:

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| Result surface | `EvidenceResultView.tsx` | Top-level result (Final Assessment, Provenance, Detectors, Coverage, OCR, QR, URLs, Metadata, Forensics, Limitations) |
| Provenance | `ImageProvenancePanel.tsx` | C2PA status, signature, signer, issuer, AI assertions |
| Forensics | `ImageForensicsPanel.tsx` | Forensic signals, limitations, raw values |
| Metadata | `ImageMetadataPanel.tsx` | EXIF, format, dimensions, camera, GPS flag |
| OCR | `EvidenceResultView.tsx` (OcrPanel) | Engine, confidence, text, lines, Arabic limitation |
| QR | `EvidenceResultView.tsx` (QrPanel) | Payload, decode status, isUrl |
| URLs | `EvidenceResultView.tsx` (UrlPanel) | Normalized candidate, risk, trust, origin, repair |
| Timeline | `InvestigationTimeline.tsx`, `TimelineView.tsx` | Analysis events |
| Graph | `EvidenceGraphView.tsx` | Evidence nodes, relationships |
| Coverage | `EvidenceResultView.tsx` (AnalysisCoverage) | Ran/did-not-run per branch |
| Hero | `ResultHero.tsx` | Verdict, gauge, status row |
| Gauge | `EvidenceCompassGauge.tsx` | Visual gauge |

### Backend response structure (evidence):

```json
{
  "analysisType": "evidence",
  "mode": "image",
  "fileName": "...",
  "fileSizeBytes": 12345,
  "provenance": { "status", "manifestFound", "signatureVerified", ... },
  "ensemble": { "detectors", "detectorAgreement", "evidenceQuality", "distributionStatus", "syntheticLikelihood", ... },
  "ocr": { "engine", "enginesUsed", "confidence", "text", "lines", "containsArabic", ... },
  "qr": { "decodeStatus", "attemptUsed", "isUrl", "payload", ... },
  "urls": [ { "normalizedCandidate", "repairApplied", "urlIntelligence", "origin", ... } ],
  "metadata": { "format", "width", "height", "exifPresent", "cameraMake", ... },
  "forensics": [ { "name", "value", "meaningEn", "doesNotMeanEn" } ],
  "evidenceQuality": { "longEdge", "lowResolution", "warnings" },
  "fusion": { "finalAssessment", "findings", "evidenceHierarchy", "limitations", "note" },
  "timeline": [ { "stage", "status", "detail" } ],
  "coverage": { "imagePixels", "provenance", "ocr", "qr", "url", "encoding", "fileStructure" },
  "reportTraceability": [ "F-001", ... ],
  "latencyMs": { ... },
  "fingerprint": "sha256"
}
```

### Facts / Inferences / Uncertainties model:

- **Observed facts** come from backend fields: `fileName`, `fileSizeBytes`, `metadata.format`, `metadata.width`, `metadata.height`, `provenance.status`, `qr.decodeStatus`, `ocr.engine`, `forensics` signals, `coverage`
- **Model inferences** come from: `ensemble.detectorAgreement`, `ensemble.evidenceQuality`, `ensemble.distributionStatus`, `ensemble.syntheticLikelihood`
- **Uncertainties** come from: `assessment === 'uncertain'`, `ensemble.abstained`, `provenance.status === 'unavailable'`, `modeConflict`, `limitations`

### Key contract rules already enforced:

- `syntheticLikelihood` is `number | null` (null on conflict — never invented)
- `finalAssessment` is canonical (uncertain for single-detector cases)
- `trustScore` is null for image (deprecated)
- Confidence is `number | null` (null = not published, not 0)
- GPS is boolean-only (coordinates never shown)
- Provenance states: `verified`, `present_unverified`, `invalid`, `unavailable`

## Known issues to fix:

1. **"Illuminate" Arabic graph label** — untranslated English in Arabic mode (in `translations.ts`)
2. **OCR "raw" dumping** — OCR text shown in primary panel (should be collapsed)
3. **No Facts/Inferences/Uncertainties separation** — all evidence blended in panels
4. **No Missing Evidence section** — "not found" items not explicitly flagged
5. **No Correlated Finding section** — cross-modal correlation not presented
6. **No Conflict Presentation** — detector disagreement not shown as conflict
7. **No Evidence Traceability** — no F-ID/E-ID traceability links
8. **No definitive documentation** — docs/PHASE5_STAGE3_EVIDENCE_EXPERIENCE.md, docs/EVIDENCE_MODEL.md, docs/EVIDENCE_TRACEABILITY.md

## Implementation Plan

1. Audit complete (this file)
2. Add Facts/Inferences/Uncertainties separation components
3. Improve OCR panel (usable vs raw, collapsed)
4. Improve QR panel (decoded type, normalized domain, no auto-nav)
5. Add URL intelligence (visible/extract/normalize/actual, syntax validation)
6. Improve metadata presentation (basic vs image vs EXIF vs interpretation)
7. Improve forensics (signal/measured/interpretation/limitation)
8. Add Missing Evidence section
9. Add Correlated Finding section
10. Add Conflict Presentation
11. Add Evidence Traceability
12. Polish Arabic/English
13. Accessibility/responsiveness
14. Tests
15. Real browser QA
16. Documentation
17. Final gates
