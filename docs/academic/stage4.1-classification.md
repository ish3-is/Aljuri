BASIRAH STAGE 4.1 — REPOSITORY CLEANUP CLASSIFICATION
====================================================
Project root: D:\MDR\Aljuri-Greadute-Project

Classification (produced before any deletion).
No files deleted yet; updates to .gitignore, README, .env.example first.

------------------------------------------------------------------
A. KEEP — EXPECTED PUBLIC PROJECT CONTENT
------------------------------------------------------------------
Frontend (basirah/):
  KEEP  src/                      — production source
  KEEP  public/                   — static assets (Logo.png etc.)
  KEEP  package.json              — frontend deps (exact)
  KEEP  package-lock.json         — reproducible installs
  KEEP  vite.config.ts            — config
  KEEP  tsconfig*.json            — TS config
  KEEP  eslint.config.js          — lint config
  KEEP  index.html                — entry
  KEEP  .env.example              — placeholder env example
  KEEP  README.md                 — to be rewritten (Section 12)
  KEEP  src/styles/index.css      — primary stylesheet
  KEEP  src/features/             — production app features
  KEEP  src/components/           — production components
  KEEP  artifacts/ (staged)       — report screenshots (eventually)

Backend (backend/):
  KEEP  app/                      — production backend (FastAPI)
  KEEP  tests/                    — pytest suite
  KEEP  requirements.txt          — production deps (exact pins)
  KEEP  app/main.py, app/schemas/, etc. — production code
  KEEP  relevant eval scripts     — run_phase2e_experiment.py,
          run_phase37_detector_b.py, verify_baseline.py, etc.
  KEEP  datasets/dev_fixture_urls.csv — dev fixture (documented)
  KEEP  evaluation/               — evaluation artifacts
  KEEP  docs/                     — existing docs
  KEEP  _run-checks.sh            — developer-useful QC script

Project root:
  KEEP  docs/academic/            — Stage 4 evidence pack (new)
  KEEP  docs/DEPLOYMENT_READINESS.md (new)
  KEEP  README.md (rewritten in Stage 4)
  KEEP  LICENSE                      (new)
  KEEP  .gitignore                  (new, root-level) + backend/.gitignore
  KEEP  .env.example (frontend)   — placeholder only

------------------------------------------------------------------
B. GITIGNORE — NEW ROOT .gitignore (create)
------------------------------------------------------------------
node_modules/
dist/
.vite/
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
.env.*
!.env.example
*.log
logs/
.DS_Store
Thumbs.db
.vscode/
.idea/
artifacts/
screenshots/
coverage/
htmlcov/
tmp/
temp/
*.tmp
*.bak
datasets/image/raw/
datasets/raw/
models/*.joblib
models/*.pt
models/*.pth
models/*.onnx

------------------------------------------------------------------
C. REMOVE BEFORE PUBLICATION
------------------------------------------------------------------
Agent/AI instruction files (none present — scan clean):
  No AGENTS.md / CLAUDE.md / copilot-instructions.md / .cursor/ / .claude/
  / .hermes/ / .agent/ / .ai/ / .codex/ found. (Content scan matched only
  legitimate project words like "algorithm"/"agent-based" in source/docs.)

Temporary QA / debug scripts (frontend basirah/scripts/):
  REMOVE
    compute-offenders.mjs
    verify-closure.mjs, verify_closure2.mjs
    verify_gemini_old.mjs, verify_gemini_frontend2/3/4/5.mjs
    verify_live_browser.mjs
    verify_live_stage2.mjs
    verify-states.mjs
    dump-gemini-text.mjs

    diag-*.mjs (8): diag-computed, diag-css, diag-current, diag-evidence,
                     diag-full, diag-full2, diag-inner, diag-main, diag-mobile-final,
                     diag-overflow, diag-resultview, diag-resultview2, diag-wide, diag-wide2
    (15 files; consolidate into ONE generic script is possible but task says
     do not spend large effort refactoring; these are temporary QA/debug)

    stage3-*.mjs (stage3-final-ac.mjs, stage3-live-qa.mjs, stage3-responsive-final.mjs)
    stage3-final-ac.mjs, stage3-live-qa.mjs, stage3-responsive-final.mjs,
    stage3-final-results.json, stage3-responsive-results.json,
    stage3-results.json, stage3-micro-qa-final.json/.log,
    stage3-final.log, stage3-qa.log, stage3-responsive.log,
    stage3-final-results.json

    debug-frontend.mjs, diag-*.mjs (15 files) - temp QA/debug

    run_live_stage2.sh (old bash service launcher; replaced by stage3 scripts)
    trim-assets.mjs (one-off)

    stage3-final.log, stage3-qa.log, stage3-responsive.log (logs)

    compute-offenders.mjs, stage3-final-results.json, stage3-responsive-results.json,
    stage3-results.json, stage3-micro-qa-final.json/.log (temp QA artifacts)

Temporary QA/debug scripts (backend):
  REMOVE
    _fi.py
    _fix_magic.py
    _fr2.py
    cleanup_pydantic.py
    analyze_thresholds.py
    compute_abstention.py
    compute_group_metrics.py
    audit_operating_points.py
    verify_abstention.py

    NOTE: keep train_url_model.py and train_image_models.py as they are the
    reproducible model-training entry points. Keep evaluate_url_model.py.

Temporary QA files (backend):
  REMOVE
    backend.log
    test_minimal.png

Temporary QA files (frontend):
  REMOVE
    stage3-final.log, stage3-qa.log, stage3-responsive.log
    stage3-final-results.json, stage3-responsive-results.json,
    stage3-results.json, stage3-micro-qa-final.json/.log
    compute-offenders.mjs, trim-assets.mjs, stage3-final-ac.mjs

Review — backend scratch startup scripts (task §5):
  _run-checks.sh (frontend) — developer-useful QC script → KEEP
  start_backend.py, start_server.py (backend) — developer-useful startup
    scripts → KEEP (rename to a professional name)
  _fi.py, _fix_magic.py, _fr2.py, cleanup_pydantic.py — temporary repair
    artifacts → REMOVE

  NOTE: If a startup script is useful, rename/document professionally.
    Proposed professional names:
      backend/scripts/start_backend.sh   (or start_backend.py)
      backend/scripts/start_frontend.sh  (rename run_live_stage2.sh)
    For §6, we keep them but rename.

------------------------------------------------------------------
D. REVIEW MANUALLY (do not delete)
------------------------------------------------------------------
  basirah/qa/            (10 browser/QA scripts: browser_test, qa-p37,
                          qa-light-regress, qa-light-visual, qa-reports,
                          root_cause_test, run-qa, run-qa-p36, run-qa-refresh,
                          serve-dist) — repeatable QA, review manually
  basirah/scripts/       (verify-ui.mjs, verify-wording.mjs, verify-excel-sanitiser.mjs,
                          debug-frontend.mjs, diag-*.mjs, stage3-*.mjs,
                          trim-assets.mjs, verify-live-stage2.mjs) — mix of QA and
                          temporary
  backend/scripts/       (28 scripts incl. train_url_model.py,
                          train_image_models.py, run_phase2e_experiment.py,
                          run_phase37_detector_b.py, evaluate_url_model.py,
                          e2e_image_flow.py, probe_rows_api.py, test_filter_api.py,
                          test_range_parquet.py, make_c2pa_fixtures.py, etc.)
  backend/datasets/      (dev_fixture_urls.csv - dev fixture; image/ corpora)
  backend/evaluation/    (evaluation artifacts)
  basirah/Logo.png, basirah/UNI_LOGO.png — project assets
  basirah/README.md, basirah/CLOSURE_REPORT.md — docs (to be rewritten)
  backend/README.md      — backend docs
  basirah/artifacts/, basirah/screenshots/ — staged screenshots

------------------------------------------------------------------
QUALITATIVE RULES
------------------------------------------------------------------
1. Do NOT delete every script; only clearly-temporary scratch/repair scripts.
2. If a startup script is useful, rename it professionally rather than
   deleting blindly.
3. Keep boundary line: model retraining / threshold changes / deployment — none.
4. PUBLIC API (no GitHub push yet) — this is cleanup only; do not push.

NEXT STEP:
  After classification above, execute cleanup:
    1. Write root .gitignore
    2. Rewrite README.md (Section 12)
    3. Update .env.example (Section 11)
    4. Delete REMOVE BEFORE PUBLICATION files
    5. Rename KEEP startup scripts professionally
    6. Rescan secret/path after cleanup
    7. Final static gates
