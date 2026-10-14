# Evidence Model

## The three-way separation

Every finding on a BASIRAH result page is one of three things:

| Category | What it is | Example |
|----------|-----------|---------|
| **Observed Facts** | What was actually measured or read off the file | file name, SHA-256, image dimensions, QR payload decoded, OCR text returned, EXIF fields present, C2PA manifest detected, signature validation result |
| **Model Inferences** | What the models concluded from those measurements | likely synthetic, URL risk estimate, OOD classification, detector synthetic score, suspicious-domain interpretation, compression anomaly interpretation |
| **Uncertainties** | What could not be verified | detector disagreement, analyzer unavailable, OCR ambiguity, missing provenance, unknown generator family, OOD, low-resolution limitation |

The backend returns raw measurements. The frontend is responsible for:

1. **Not mixing categories visually** — each category gets its own panel/section with a distinct visual treatment.
2. **Using existing backend fields only** — no fabrication of confidence values, timestamps, or relationships.
3. **Showing uncertainty explicitly** — when evidence is missing, present it as a finding, not a blank.

## Evidence taxonomy

```
Evidence
├── Observed Facts
│   ├── File metadata        (fileName, fileSizeBytes, SHA-256)
│   ├── Image metadata       (format, dimensions, EXIF fields)
│   ├── QR evidence          (decoded payload, decoded type)
│   ├── OCR evidence         (extracted text, detected language, entities)
│   ├── URL evidence         (visible URL, extracted URL, normalized URL)
│   ├── Provenance           (manifest presence, signature status)
│   ├── Forensics            (compression anomaly, noise floor, dimensions)
│   └── Coverage             (which analyzers ran / skipped / unavailable)
├── Model Inferences
│   ├── Detector A opinion   (synthetic probability, status)
│   ├── Detector B opinion   (synthetic probability, status)
│   ├── Ensemble agreement   (strong / conflict / abstained)
│   ├── Distribution status  (in / borderline / OOD)
│   └── Risk classification  (caution / high_risk / trusted)
└── Uncertainties
    ├── Missing provenance   (no manifest found)
    ├── Detector conflict    (detectors agree on nothing)
    ├── Low resolution       (too small for reliable analysis)
    ├── Offline model        (model unavailable)
    └── Unsupported structure (file type not analyzable)
```

## Finding contracts

### F-ID (Finding ID)

Every meaningful finding gets a deterministic ID:

```
F-001  Verified provenance assertion (C2PA)
F-002  Detector A: likely synthetic (P=0.91)
F-003  Detector B: likely authentic (P=0.87)
F-004  Detector conflict: A vs B disagree
F-005  OCR: extracted a URL (paypal.com)
F-006  QR: decoded a URL (paypa1-security.example)
F-007  Displayed domain mismatch (paypal.com vs paypa1-security.example)
F-008  Confirmed URL: high-risk destination
F-009  Metadata: Photoshop software record
F-010  Low-resolution limitation
F-011  OCR: no text extracted
F-012  No provenance manifest
```

Same evidence → same IDs. Deterministic.

### E-ID (Evidence ID)

Every piece of source evidence gets an E-ID:

```
E-001  SHA-256 of uploaded file
E-002  OCR text line 1
E-003  QR payload
E-004  Extracted URL
E-005  EXIF DateTimeOriginal
E-006  C2PA manifest
E-007  Forensic signal: compression_anomaly
```

### Traceability

A finding may reference E-IDs that support it:

```
F-003 (QR: suspicious URL)
  Supported by:
    E-003 (QR payload)
    E-004 (URL intelligence)
```

## Analyzer status semantics

| Status | User-facing label | Meaning |
|--------|------------------|---------|
| `completed` | Ran | The analyzer executed and produced a result |
| `skipped` | Not run | The pipeline did not run this analyzer (e.g. non-image upload) |
| `unavailable` | Unavailable | The analyzer could not run (e.g. OCR engine missing) |
| `failed` | Failed | The analyzer ran but an error occurred |
| `not_applicable` | N/A | The analyzer is not applicable to this signal type |
| `shadow_only` | Shadow only | Detector B is a shadow-only diagnostic, not a production detector |

## Provenance states

| State | User-facing label | Meaning |
|-------|-------------------|---------|
| `verified` | Verified | Manifest present, signature validated, claims assessed |
| `present_unverified` | Present, unverified | Manifest found but signature validation failed or was skipped |
| `invalid` | Invalid | Manifest present but claims failed validation |
| `unavailable` | Unavailable | No manifest found |

## OCR classification

OCR output is classified into three tiers:

| Tier | Definition | Display |
|------|-----------|---------|
| **Usable Extracted Text** | Well-formed, language-detected, contains readable sentences | Primary panel |
| **Detected Entities / Indicators** | URLs, emails, domains extracted from raw OCR | Primary panel |
| **Raw OCR Output** | Unfiltered, low-quality, noisy | Collapsed by default |

If confidence is unavailable: show "Confidence unavailable". Never invent a percentage.

## URL evidence types

| Type | Meaning |
|------|---------|
| **Visible URL** | Text visible in the image/screenshot (where applicable) |
| **Extracted URL** | URL recovered from QR, OCR, or screenshot text |
| **Normalized URL** | Extracted URL after normalization (IDN, punycode) |
| **Actual Analysed URL** | The URL that went through the URL intelligence pipeline |

If OCR produces an invalid URL: do not promote it as a verified indicator. Validate syntax before correlation.

## Evidence coverage

| Status | Label | Meaning |
|--------|-------|---------|
| `analyzed` | Ran | The analyzer executed and produced a result |
| `not_applicable` | N/A | Analyzer not applicable to this signal type |
| `unavailable` | Unavailable | Analyzer could not run |
| `failed` | Failed | Analyzer ran but errored (rare — the pipeline uses `not_applicable` for skipped) |

## Provenance semantics

| State | What to say |
|-------|------------|
| `verified` | "A Content Credentials manifest was validated and claims assessed." Do not imply universal truthfulness. |
| `present_unverified` | "A manifest was found but validation failed or was skipped." |
| `invalid` | "A Content Credentials manifest is present, but validation failed." Do NOT say "AI-generated". |
| `unavailable` | "No verifiable Content Credentials manifest was found." Do NOT say "not authentic". |

## Cross-modal correlation

When evidence from different modalities supports or conflicts with each other:

```
CORRELATED FINDING
  OCR text contains "paypal.com" (E-005)
  QR code decoded to "paypa1-security.example" (E-003)
  Discrepancy: visible domain vs embedded destination
  Source references: E-003, E-005
```

Do not merge unrelated evidence into one claim. Show the sources.

## Conflict presentation

When evidence conflicts, present each source separately:

| Source | Claim |
|--------|-------|
| Detector A | Likely synthetic (P=0.91) |
| Detector B | Likely authentic (P=0.87) |
| Conflict | Detectors disagree — no combined likelihood is published |

## Missing evidence

Show only when it materially affects interpretation:

- No provenance (material to authenticity claims)
- OCR unavailable (raw OCR cannot be checked)
- No QR detected (no QR evidence to evaluate)
- URL not analyzable (extracted URLs could not be scored)
- Unsupported file structure (file could not be inspected)

## Timeline

| Timeline type | Contents |
|--------------|----------|
| **Analysis Timeline** | Evidence received, validation completed, metadata inspected, provenance inspected, OCR completed, QR completed, URL analysis completed, detector analysis completed, correlation completed, assessment prepared |
| **Content History** | Only C2PA/provenance timestamps (e.g. EXIF DateTimeOriginal) — labeled as metadata, not verified historical facts |

## Evidence traceability

Each finding that references source evidence shows:

```
F-003 (QR: suspicious URL)
  Supported by:
    E-003 QR payload
    E-004 URL analysis
```

## Performance considerations

- Lazy-render heavy technical content (raw OCR, raw provenance payload, raw metadata, raw model scores)
- SVG gauge/graph renders at typical sizes; no virtualization needed unless graphs exceed 50 nodes
- Large OCR text: keep in scrollable container
- Metadata lists: compact field rows

## Arabic/English

Must be natural, not literal:
- Observed Facts → الحقائق المرصودة
- Model Inferences → استنتاجات النماذج
- Uncertainties → حالات عدم اليقين
- Evidence → الأدلة
- Finding → النتيجة التحليلية
- Provenance → بيانات المنشأ
- Evidence Graph → شبكة الأدلة
- Analysis Timeline → التسلسل الزمني للتحليل
- Evidence Coverage → تغطية التحليل
- Detector Conflict → تعارض الكاشفين
- Unavailable → غير متاح
- Invalid → غير صالح
