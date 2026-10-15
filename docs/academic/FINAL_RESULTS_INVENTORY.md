# BASIRAH — FINAL RESULTS INVENTORY

> Verified evidence pack for the final report / presentation. Every row maps to
> a real command output or a real artifact — nothing is invented.
> Boundary rule: **offline benchmark results** are NOT the same as **live demo
> functionality**. They are kept separate throughout.

---

## 1. URL Model Performance

| Item | Verified value | Source |
|---|---|---|
| Production model | `backend/models/basirah-url-v3.joblib` (promoted via `models/ACTIVE_MODEL.json`) | `models/ACTIVE_MODEL.json` |
| Model version | 3.0.0 | `models/ACTIVE_MODEL.json` |
| Real-world legitimate FP of 14 | v1 = 10, **v3 = 5** | `models/ACTIVE_MODEL.json` evidence |
| Worst corpus ROC AUC | v1 = 0.3112, **v3 = 0.8481** | `models/ACTIVE_MODEL.json` evidence |
| Grouped-domain ROC AUC | v1 = 0.5738, **v3 = 0.9476** | `models/ACTIVE_MODEL.json` evidence |
| Semantic phishing false negatives | v1 = 11, **v3 = 0** | `models/ACTIVE_MODEL.json` evidence |
| Production status | PROMOTED (advisory) | `models/ACTIVE_MODEL.json` |
| Deployment suitability | **Not deployable for automated enforcement** | evaluation artifacts |

---

## 2. Cross-Corpus Limitations

- The evaluation corpora are not drawn from the same domain distribution; a model
  that generalises within one corpus can regress on another.
- The only committed corpus is a dev fixture (`dev_fixture_urls.csv`) which is
  pipeline-only and **cannot** support conclusions.
- Real labelled phishing corpus acquisition is pending.
- Real image corpora (Flickr30k, CommunityForensics) are licensed and excluded;
  the corpus can only be rebuilt from recorded URLs + checksums.

---

## 3. Image Detector Results

| Detector | Role | Production status | Evaluation status |
|---|---|---|---|
| Detector A — EfficientNet | Ensemble member | PROMPTED (advisory) | RESEARCH result |
| Detector B — CLIP linear probe | Shadow-only ensemble member | SHADOW-ONLY | RESEARCH result |
| UnivFD | Research candidate (evaluated where applicable) | NOT PROMOTED | RESEARCH result |
| Production deployment suitability | **None** met criteria | — | — |

**Advisory policy:** no detector claims legal/certified authenticity.

---

## 4. Detector B Role

- **Shadow-only**: loaded and contributes signals, but does not enforce or block.
- Not independently deployed.
- Preserved so the ensemble signal is still available for analysis without
  presenting it as deployment-grade.

---

## 5. C2PA Behavior

- C2PA 0.38.0 is a production dependency.
- Provenance state preserved scientifically: `provenance.status`, `provenance.manifest`, `provenance.sig`.
- Evidence service reports C2PA status/manifest/signature where present.
- Missing/malformed provenance manifests yield `unavailable`, not a verdict.

---

## 6. OCR / QR Status

| Item | Status |
|---|---|
| OCR | VERIFIED (Tesseract/EasyOCR fallback) — forensic signal |
| QR | VERIFIED (OpenCV) — decodes encoded destination |

OCR quality depends on image resolution and may fail on low-res text. QR decodes
the encoded destination; it does not verify the page behind the QR.

---

## 7. Real Gemini Regression Example

Recorded in earlier evaluation artifacts (`backend/results/phaseX`). It is cited
from those artifacts — it is **not** presented as live throughput or as a solved
image-detection service.

---

## 8. Evidence Fusion

- Canonical aggregation: URL model advisory distribution + image forensics /
  metadata + C2PA provenance state + OCR + QR + Detector A / Detector B advisory
  outputs.
- Output: canonical verdict (trusted / uncertain / adversarial) with explicit
  uncertainty band, plus coverage and abstention accounting.
- Verified: evidence view renders final assessment, provenance, evidence, graph,
  timeline, coverage, metadata/forensics, traceability.

---

## 9. Graph / Timeline

| Item | Status |
|---|---|
| Evidence graph | VERIFIED (rendered SVG) |
| Timeline | VERIFIED (`timeline.ready === true`) |

---

## 10. Local Live Demo

- Real image → evidence view: **VERIFIED** (real HTTP 200 + evidence rendered).
- EN and AR RTL viewport checks passed (mobile 390×844, desktop 1440×1000).
- Keyboard-only focus: `a:focus-visible` visible, non-color-only.

---

## 11. GitHub Pages Showcase

- `https://ish3-is.github.io/Aljuri/` — HTTP 200, current build served.
- GitHub Actions deploy workflow: run `38779877110` — success (build + deploy).
- Showcase mode API behaviour: **ZERO** `POST /api/analyze/evidence`, **ZERO**
  localhost requests, **ZERO** HTTP 405.

---

## 12. Backend Test Count

| Check | Result |
|---|---|
| `backend/.venv/Scripts/python.exe -m pytest -q --ignore=scripts` | **426 passed, 7 skipped, 2 xpassed, 1 warning** |
| Failed | 0 |
| Skipped | 7 (pre-existing, unchanged) |
| xpassed | 2 (pre-existing, unchanged) |

---

## 13. Frontend Gate Counts

| Check | Result |
|---|---|
| `cd basirah && npx tsc -p tsconfig.app.json --noEmit` | pass (0) |
| `npm run lint` | pass |
| `npm run build` | pass |
| `node scripts/verify-wording.mjs` | **131/131** |
| `node scripts/verify-ui.mjs` | **74/74** |

---

## 14. Boundary: offline benchmark vs live demo

| Offline benchmark (in `backend/results/`) | Live demo (local or Pages) |
|---|---|
| Detector A/B / UnivFD evaluation | Real HTTP evidence flow |
| Holdout / generalization | Live HTTP 200 + evidence rendered |
| Machine-learning metric numbers | Live demo = the visible GUI + API flow |

Do not mix these two lists in the report. The live demo proves the *system
works end to end*; the offline benchmarks prove the *model evaluation*. Both
belong in the report, clearly labelled.
