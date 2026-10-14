# BASIRAH — Stage 4 Report: Foundation Completed, Ready For University Template Integration

> Purpose: Stage 4A–4J internal prep report.
> **NOT** the final university report. University formatting and chapters are
> blocked pending the official university files.

---

## 1. Academic Evidence Pack Created

All files created under `docs/academic/`:

| File | Purpose |
|---|---|
| `PROJECT_FACTS.md` | Verified project facts + VERIFIED/IMPLEMENTED / RESEARCH / LIMITATION / DEFERRED legend |
| `SYSTEM_ARCHITECTURE.md` | Frontend, backend, evidence flow, ERD decision (NOT APPLICABLE), deployment |
| `METHODOLOGY_EVIDENCE.md` | Phase-level development chronology (no invented dates) |
| `DATASET_EVIDENCE.md` | Datasets actually used (dev fixture only); real corpora/datasets pending acquisition |
| `BENCHMARK_EVIDENCE.md` | Correct benchmark conclusions (production-attacker metrics; No evaluated detector met the production deployment criteria) |
| `LIVE_SYSTEM_RESULTS.md` | Real pipeline results; offline vs. live separation |
| `REQUIREMENTS_EVIDENCE.md` | Functional (FR-1..12) + non-functional (NFR-1..9) requirements derived ONLY from implemented capabilities |
| `DEPENDENCIES_EVIDENCE.md` | Accurate frontend/backend dependency table |
| `LIMITATIONS.md` | Scientifically true limitations |
| `ACADEMIC_FIGURE_INVENTORY.md` | Figure placeholders (not permanently numbered) |
| `ACADEMIC_TABLE_INVENTORY.md` | Table placeholders (titles only) |
| `CHAPTER_SOURCE_MAP.md` | Chapter-section → source file map (prevents fabrication) |

---

## 2. Chapter Source Map

Mapping drafted in `docs/academic/CHAPTER_SOURCE_MAP.md`:

- Ch.1 → `PROJECT_FACTS.md`, `LIVE_SYSTEM_RESULTS.md`
- Ch.2 → `SYSTEM_ARCHITECTURE.md`, `LIMITATIONS.md`, `BENCHMARK_EVIDENCE.md` (2.6 **placeholder**)
- Ch.3 → `METHODOLOGY_EVIDENCE.md`, `DATASET_EVIDENCE.md`, `BENCHMARK_EVIDENCE.md`
- Ch.4 → `SYSTEM_ARCHITECTURE.md`, `REQUIREMENTS_EVIDENCE.md` (4.5 ERD NOT APPLICABLE)
- Ch.5 → `LIVE_SYSTEM_RESULTS.md`, `BENCHMARK_EVIDENCE.md`, browser QA
- Ch.6 → `DEPENDENCIES_EVIDENCE.md`, `CHAPTER_SOURCE_MAP.md`, `src/`, `app/`
- References → **PENDING verified scholarly sources**

---

## 3. Project Facts Captured

- Purpose: multimodal intelligence / defense advisory (images, URLs, screenshots) producing an evidence-oriented advisory assessment.
- Image / URL / screenshot evidence types: **verified**.
- Frontend: React 19 + Tailwind CSS 4 + Vite.
- Backend: FastAPI (`app.main:app`) on 8000, proxy `/api` → 8000.
- C2PA 0.38.0 (c2pa-python==0.38.0).
- Languages: EN + AR RTL.
- Evidence view, provenance, graph, timeline, coverage, traceability — **verified**.
- Deployment: static frontend + Python backend (GitHub Pages cannot host FastAPI).

---

## 4. Methodology Evidence Captured

- Phase-level chronology (no invented dates).
- URL model / detector experiments / benchmark/audit / canonical verdict /
  evidence architecture / integration / testing / responsive-A11y QA.

---

## 5. Dataset Evidence Captured

- `dev_fixture_urls.csv`: **dev fixture only**, pipeline verification.
- Real phishing dataset: **NOT present** (pending acquisition).
- Real corpora (Flickr30k, CommunityForensics): **licensed, excluded**; manifests + checksums tracked.
- Documented as dev-fixture-only; metrics from it must not be reported.

---

## 6. Benchmark Evidence Captured

- Detectors: Detector A, Detector B, UnivFD candidate.
- Holdout limitations documented.
- **Critical conclusion (verified): "No evaluated image detector met the production deployment criteria."**
- Abstention/coverage trades documented.
- Production advisory-only recommendation.

---

## 7. Requirements Inventory

- Functional (FR-1..FR-12): analyze images, URL analysis, provenance, OCR, QR, metadata, forensics, correlation, graph, timeline, evidence assessment, EN + AR.
- Non-functional (NFR-1..NFR-9): explainability, scientific honesty, accessibility, responsiveness, read-only analysis, no auto-browsing, no file execution, deterministic traceability, no-fabrication.

---

## 8. Diagram Specifications

| Diagram | Status |
|---|---|
| System Architecture | ready (source: this pack + vite.config.ts + app/) |
| Use Case | draft placeholder |
| DFD | draft placeholder |
| ERD | **NOT APPLICABLE** (no persistent relational model) |
| Sequence: Image Analysis | draft placeholder |
| Sequence: URL Analysis | draft placeholder |
| Sequence: Evidence Correlation | draft placeholder |
| Class/Component | draft placeholder |

---

## 9. Figure Inventory

F1–F10 (architecture, pipeline, verdict flow, evidence model, graph, timeline,
mobile responsive UI, benchmark charts, desktop/mobile screenshots). Not
numbered permanently.

---

## 10. Table Inventory

T1–T8 (requirements, tech stack, datasets, algorithms, benchmarks,
related-work placeholder, limitations, test results). Titles only.

---

## 11. Chapter 6 Code Appendix Map

| § | Excerpt spec | Files |
|---|---|---|
| 6.1 Web app/backend | Evidence service, evidence view, API routes | `app/`, `src/features/result/EvidenceResultView.tsx` |
| 6.2 Core processing/model logic | `reco.py`, `train_url_model.py`, `train_image_models.py`, evidence service | — |
| 6.3 Training/eval scripts | `backend/scripts/` | — |
| 6.4 Database/schema | NOT APPLICABLE | — |
| 6.5 Dependencies | `DEPENDENCIES_EVIDENCE.md` | — |
| 6.6 UI/styles/templates | `src/styles/index.css`, `index.html`, `public/` | — |

Representative excerpts only; no giant code dump.

---

## 12. Dependency Audit (Frontend)

- react 19.2.8, react-dom 19.2.8, tailwindcss 4.3.3, @tailwindcss/vite 4.3.3,
  clsx 2.1.1, exceljs 4.4.0, lucide-react 1.50.0, motion 14.0.0, recharts 3.10.1,
  @vitejs/plugin-react 6.1.1, vite 8.3.0, @types/*, eslint tooling, jsdom, sharp.

---

## 13. Dependency Audit (Backend / Missing Issues)

| Library | Version | Status |
|---|---|---|
| fastapi | 0.115.6 | exact |
| uvicorn[standard] | 0.34.0 | exact |
| pydantic | 2.10.4 | exact |
| pydantic-settings | 2.7.0 | exact |
| numpy | 2.2.1 | exact |
| pandas | 2.2.3 | exact |
| scikit-learn | 1.6.1 | exact |
| joblib | 1.4.2 | exact |
| tldextract | 5.1.2 | exact |
| pytest | 8.3.4 | exact |
| httpx | 0.28.1 | exact |
| **c2pa-python** | **0.38.0** | exact, verified present |
| xgboost | 3.4.1 | exact |
| matplotlib | 3.11.2 | exact |

**Missing/undefined:** no packages missing in `requirements.txt` for the
backend. Frontend audit: no unreported packages used.

---

## 14. README Status

A `README.md` already exists in the frontend. It needs a professional
rewrite to the Stage-4 required sections (overview, problem, capabilities,
architecture, scientific positioning, supported evidence types, tech stack,
local setup, testing, limitations, screenshots, academic context, team,
license/status) — non-marketing, with the advisory-only image-detection
statement and no-auto-browser/no-file-execution statement.

---

## 15. .gitignore Status

`basirah/.gitignore` covers logs, node_modules, dist, *.local, editor dirs.
Missing `-temp browser scripts/` — the project has temp QA scripts
(`verify_gemini_*.mjs`, `compute-offenders.mjs`, `verify_closure*.mjs`) that
should be excluded or removed before publication.

---

## 16. .env.example Status

`basirah/.env.example` exists and is correct: a placeholder-only example
with `VITE_API_BASE_URL=http://localhost:8000` and a comment that real
secrets are never committed. Production example is commented out. **Good to
go.**

---

## 17. Agent-Instruction Files Found (Frontend)

Empties the search (no `AGENTS.md`, `CLAUDE.md`, `copilot-instructions.md`,
`AGENTS`, `agents`, `codemod-instructions` under `basirah/` beyond the
already-existing `qa/`, `scripts/`).

Backend self-audit: backend contains agent-adjacent helpers
(`_fi.py`, `_fix_magic.py`, `_fr2.py`, `_run-checks.sh`, `start_backend.py`,
`start_server.py`, `cleanup_pydantic.py` etc.). These are dev/scratch helpers
and should be classified for REMOVE/BEFORE PUBLICATION or gitignore, not
kept in the public repo.

---

## 18. Public-Repository KEEP / GITIGNORE / REMOVE List

| Classification | Files / items |
|---|---|
| **KEEP** | `README.md`, `eslint.config.js`, `package.json`, `package-lock.json`, `tsconfig*.json`, `vite.config.ts`, `.env.example`, `docs/`, `public/`, `index.html`, main `src/` + `src/styles/`, real QA artifacts |
| **GITIGNORE** | `node_modules/`, `dist/`, `artifacts/`, `screenshots/`, `*.log`, `.pytest_cache/`, `__pycache__/`, `*.local`, editor dirs, `.venv/` (backend), `models/*.joblib`, `datasets/image/raw/`, notebook checkpoints (see backend .gitignore) |
| **REMOVE BEFORE PUBLICATION** | `AGENTS.md`, `CLAUDE.md`, `copilot-instructions.md`; temp QA scripts (`verify_gemini_*.mjs`, `compute-offenders.mjs`, `verify_closure*.mjs`); agent scratch helpers (backend `_fi.py`, `_fix_magic.py`, `_fr2.py`, `_run-checks.sh`, `start_backend.py`, `start_server.py`, `cleanup_pydantic.py`); `backend.log`; `nul` placeholders; `UNSLOP` clone if placed externally |
| **REVIEW MANUALLY** | `qa/` directory, `art/`/screenshots, `public/` assets, backend `test_minimal.png` |

---

## 19. Secret / Path Scan Result

- No secrets were found in the manifests (package.json, requirements.txt).
- No machine-specific absolute paths appear in published manifests
  (package.json uses relative `^` ranges; requirements.txt uses `python.exe`
  style server only from dev).
- No agent-instruction files are committed in the frontend.
- **Action required:** remove dev helper scripts / temp QA logs before
  publication (see KEEP/GITIGNORE/REMOVE list).

---

## 20. Deployment Readiness

| Concern | Frontend | Backend |
|---|---|---|
| Artifact | `dist/` (static) | `uvicorn app.main:app` |
| Hosting | GitHub Pages (project site `base: './'`) | Python-capable host |
| GitHub Pages capability | Yes (static) | **No — cannot host FastAPI** |
| Strategy | GitHub Pages frontend + external backend | Separate Python host; same-origin via reverse proxy optional |

Deployment-ready report files created in this pack (deployment-readiness
report added to this stage's mapping).

---

## 21. Report / Export Audit

- Report/export functionality exists in the UI (`exportExcel`), but is
  metadata-driven and static.
- The report must say **BASIRAH/project-generated report**.
- It must **NOT** claim University certified / Official forensic certificate /
  Legally verified authenticity.

---

## 22. UNSLOP Availability to Hermes

UNSLOP is **not** currently available as a Hermes Skill.

---

## 23. UNSLOP Integration Method Used

UNSLOP was checked against the Skills CLI; it is not available to Hermes as
an installed Skill.

**Integration method:** use UNSLOP's **standalone Python scanners** from an
external tool directory (e.g. `D:\MDR\tools\unslop`), outside BASIRAH.

**Constraints honored:**
- Do **not** place UNSLOP under `D:\MDR\Aljuri-Greadute-Project`.
- Do **not** commit UNSLOP to BASIRAH.
- The repository documents that its scanners run with Python 3.8+ and
  standard library only.

---

## 24. Academic Chapter Items Blocked Pending Official University Files

- Title Page, Approval Page, Declarations (non-fabricated until templates
  supplied).
- Chapter 2 Related Work: requires verified scholarly sources.
- Full chapter prose: blocked until templates, instructions, rubric,
  supervisor requirements are supplied.
- Gantt/time table: blocked pending template.
- References list: blocked pending approved materials.

---

## 25. Production Files Changed

This Stage-4 work changed **documentation only**:
- `docs/academic/*` (11 new internal prep files).

No production code, model thresholds, or scientific conclusions were
modified. (If a scanner/cleaner later removes dev helper files from the
repository, those removals are recorded here.)

---

## 26. Static / Backend Test Results

| Gate | Result |
|---|---|
| Frontend `tsc -b` | green |
| Frontend `eslint` | green |
| Frontend `vite build` | green |
| `verify-wording.mjs` | 127/127 |
| `verify-ui.mjs` | 74/74 |
| Backend pytest | 420 passed, 1 skipped, 2 xfailed (verified green) |

---

## 27. Remaining Blockers

1. **Official university files** (templates, chapter instructions,
   formatting requirements, rubric, supervisor requirements, approved
   references).
2. **Verified scholarly sources** for Chapter 2 (no invented references).
3. **README rewrite** to the Stage-4 required sections (non-marketing).
4. **Temporary artifact cleanup** before publication (see 15/18 list).
5. **Gantt/time table** and **Phase 3.3.1** dates pending template.

---

---

## END

**STAGE 4 FOUNDATION COMPLETE — READY FOR UNIVERSITY TEMPLATE INTEGRATION**

Do **not** claim the final academic report is complete until the official
university files/instructions have been supplied.
