# BASIRAH — .gitignore Audit (Stage 4F)

> This file documents the .gitignore state for the public-repository cleanup.

---

## 1. Frontend `.gitignore` (basirah/.gitignore)

Current content covers:

- logs (`logs`, `*.log`, npm-debug etc.)
- node_modules, dist, dist-ssr, *.local
- editor dirs (.vscode, .idea, .DS_Store, etc.)

**Missing from this file:**

- `artifacts/` and `screenshots/` are NOT currently excluded (they are
  staged as report evidence, but staging-only).
- Temp QA scripts `verify_gemini_*.mjs`, `compute-offenders.mjs`,
  `verify_closure*.mjs` are NOT excluded.
- Temp browser scripts (none of value) are not excluded.

## 2. Backend `.gitignore` (backend/.gitignore)

Current content covers:

- Virtual environment (`.venv/`)
- Trained model artifacts (`models/*.joblib`, `models/*.metadata.json`)
- Python (`__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`)
- Local env (`.env`)
- Real datasets excluded (`datasets/*.csv` except dev_fixture_urls.csv)
- Image corpora raw manifests (not committed)
- Notebooks

Missing from this file: `dist/` (frontend artifact, should be covered by the
frontend .gitignore), `backend.log`, dev helper scripts.

## 3. Recommended Final .gitignore Additions

Add to `basirah/.gitignore`:

```
# Stage 4: staging / artifacts
artifacts/
screenshots/
*.local

# Temp QA scripts (no project value)
verify_gemini_*.mjs
compute-offenders.mjs
verify_closure*.mjs
```

## 4. Deliverable

The `docs/academic/README` in the Stage-4 pack (via `STAGE4_REPORT.md` 18)
records the KEEP / GITIGNORE / REMOVE list. No `.gitignore` in the backend
is changed by this Stage-4 document; the recommended additions are for
publication, not for committing now.
