# BASIRAH — Methodology Evidence (Internal Drafting Reference)

> Purpose: a factual development chronology for Chapter 3. Dates are
> omitted deliberately; use phase names, not invented dates.

---

## 1. Problem Definition

BASIRAH addresses a single defensive problem: **how can a non-expert decide
whether an image, URL, or screenshot is likely authentic or synthetically
manipulated, when advice services either overclaim (binary "real/fake")
or leak precise numbers they cannot defend?** The project's scientific
positioning is that the answer is a **three-way canonical verdict with an
explicit uncertainty band** (trusted / uncertain / adversarial), an evidence
view that shows **why**, provenance that is reported scientifically (C2PA
status/manifest/sig), and an abstention policy that refuses overclaim.

---

## 2. Phased Development Chronology (Phase Names, Not Dates)

This is a **fact chronology** compiled from the repository's own
artifacts. Where the timeline is not precisely dated, the phase name is
used instead.

### Phase 1 (Foundation)
- Reproducible Vite + FastAPI skeleton; `src` features scaffolded;
  `EvidenceResultView` and `EvidenceResultPipeline` primitives defined;
  evidence service, heuristics engine, and `config.py` core.
- React + TypeScript + Tailwind scaffolding; `README.md` written.

### Phase 2 (URL Intelligence Engine)
- URL model: multi-encoder transformer (`CharCNN + BERT` feature tower),
  focal-balanced loss, lightweight URL table taxonomy, abstention scoring.
- Production endpoints: `GET /api/health`, `POST /api/analyze/evidence`
  (with `mode=auto` and holdout mode).
- **Critical constraint introduced:** URL analysis is advisory only; no
  automatic browsing/fetching of user submissions; no file execution.

### Phase 3 (Evidence Experience)
- Evidence service: canonical aggregation, provenance, evidence coverage,
  graph, timeline, traceability.
- `EvidenceResultView` renders final assessment, provenance, evidence,
  graph, timeline, coverage, metadata/forensics, traceability.
- Full QA matrix: browser QA (EN/AR/RTL/desktop), filter verification,
  UI/explorer verification.

### Phase 4 (Final Delivery — this Stage 4)
- Academic evidence pack, diagrams, figure/table inventories, repository
  cleanup, deployment readiness, README, `.gitignore`, `.env.example`.

---

## 3. Research and Evaluation Work

| Area | What was done | Status |
|---|---|---|
| URL model | multi-encoder tower, focal-balanced loss, abstention scoring | **VERIFIED** |
| Image detectors | Detector A + Detector B ensemble; UnivFD candidate evaluated | **RESEARCH RESULT** |
| Benchmark / holdout | holdout split + domain-shift / leakage probes | **VERIFIED** |
| Canonical verdict | three-way policy with uncertainty band | **VERIFIED** |
| Evidence architecture | provenance / coverage / graph / timeline / coverage | **VERIFIED** |
| Frontend/backend integration | `/api/analyze/evidence` real flow | **VERIFIED** |

---

## 4. URL Model Work

- Train URL model; evaluate on a held-out split (domain shift); compute
  group metrics (benign / domain-squatting / deceptive lookalike).
- Pipeline refuses to train on the dev fixture without the
  `--allow-dev-fixture` flag; when forced, the model is marked
  `evaluated:false` with a WARNING. This is a documented limitation, not a
  baseline.

---

## 5. Image Detector Experiments

- Two production detectors (Detector A, Detector B) evaluated on image
  corpora (Flickr30k, CommunityForensics), plus a UnivFD candidate.
- False-positive and false-negative findings recorded in the benchmark
  evidence pack.
- **No evaluated detector met production deployment criteria.** This is a
  critical, retained conclusion.

---

## 6. Benchmark / Audit Work

- Blind defense test (Phase 37): held-out challenger image set with
  detector outputs recorded.
- Cross-family evaluation, robustness evaluation, and corpus classifier
  tests used to characterize abstention trades.
- All results are in `backend/results/phase37/` (blind predictions,
  detector eval, ensemble agreement, blind defense test).

---

## 7. Canonical Verdict Policy

- Three-way: **trusted / uncertain / adversarial**, with an explicit
  uncertainty band.
- The advisory image detector policy is a separate layer from the
  canonical verdict; the two do not coincide.

---

## 8. Evidence Architecture

- Provenance (C2PA): status/manifest/sig preserved scientifically.
- Evidence coverage and abstention.
- Evidence graph (rendered in the result view).
- Analysis timeline (rendered in the result view).
- Traceability with real IDs only.

---

## 9. Frontend / Backend Integration

- Real UI → `POST /api/analyze/evidence?mode=auto` → HTTP 200 →
  EvidenceResultView rendered. No mock responses.

---

## 10. Testing

- Backend pytest suite (verified green: 420 passed, 1 skipped, 2 xfailed).
- Frontend: tsc (build with `tsc -b`), eslint, vite build, verify-wording,
  verify-ui.

---

## 11. Responsive / Accessibility QA

- Mobile 390×844: EN and AR RTL — scrollWidth == innerWidth after fix
  (long SHA hashes wrap, drift glows constrained, ticker track capped).
- Desktop 1440×1000 EN and AR RTL — no regression.
- Keyboard-only: Tab through links, visible focus ring (`a:focus-visible`).
