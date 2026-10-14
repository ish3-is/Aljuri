# BASIRAH — Deployment Readiness Report (Stage 4.2)

> Purpose: deployment architecture audit and production-readiness verification.
> No deployment executed. This is a readiness report only.

---

## 1. Project Identity

| Concern | Value |
|---|---|
| Repository | https://github.com/ish3-is/Aljuri |
| Project identity | BASIRAH \| بصيرة (Digital Trust Intelligence) |
| Stage | 4.2 — Public Repository Hygiene + Deployment Readiness |
| Branch | main |

---

## 2. Frontend

| Concern | State |
|---|---|
| Framework | React + TypeScript + Vite |
| Dev server port | 5199 (`basirah/vite.config.ts`, `strictPort: true`) |
| Router | SPA; rendered by the static host. No `<Router>` in source — top-level app shell drives navigation |
| Base path | `'./'` (project-site deployable at any GitHub Pages path) |
| Static assets | Hashed at build time; same-origin `/api` proxy in dev |
| API base strategy | `VITE_API_BASE_URL` (env) — empty string = same-origin `/api`; set to external HTTPS backend origin in production |
| Dev proxy (`vite.config.ts`) | `/api` → `http://127.0.0.1:8000`, `changeOrigin: true`, `secure: false` |
| Dev env | `BASIRAH_ENV=development` |

### Production API strategy

- `basirah/src/features/analysis/providers.ts` resolves `API_BASE_URL` from `VITE_API_BASE_URL` (trimmed of trailing slashes) or falls back to the empty string (same-origin `/api`).
- `resolveApiBase()` returns `''` in development, so browser code always calls `/api` on the same origin during dev. The Vite dev server proxies `/api` to `http://127.0.0.1:8000`. This means the browser never touches `localhost`/`127.0.0.1` in production.
- Production: set `VITE_API_BASE_URL=https://your-backend.example.com` (no trailing slash). The frontend bundles and calls the backend through that origin.
- **No hardcoded production URL** — the value is injected at build time and can be set via the GitHub Pages workflow variable or a `.env` file at build time.

---

## 3. Backend

| Concern | State |
|---|---|
| Framework | FastAPI + uvicorn |
| Artifact | `uvicorn app.main:app` |
| Dev port | 8000 (`http://127.0.0.1:8000`) |
| Dev CORS | `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:4173`, `http://127.0.0.1:4173` |
| Production CORS | `BASIRAH_CORS_ORIGINS` env var (comma-separated origins). GitHub Pages origin `https://ish3-is.github.io` must be added explicitly. No wildcard `*`. |

### Production start command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Cloud providers commonly inject `PORT`; the app reads no other port. Development can continue to use port 8000.

### Health endpoint

`GET /health` (FastAPI `/health` plus a `/health` liveness alias registered on the root router) — lightweight, no inference, reports:

- `status: ok`
- `service`, `version`, `phase`
- `model_available` (truthful per-artifact status)
- rule/feature counts for the URL engine

### CORS production configuration

- Dev: explicit localhost origins only.
- Production: add `https://ish3-is.github.io` to `BASIRAH_CORS_ORIGINS`. No wildcard, no `allow_credentials=True`.
- Change: add the origin via env var at deploy time. No code change.

### Linux deployment audit

| Dependency | Status |
|---|---|
| Python | 3.12+ required (`backend/requirements.txt` pins `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `pydantic==2.10.4`, `pydantic-settings==2.7.0`, `numpy==2.2.1`, `pandas==2.2.3`, `scikit-learn==1.6.1`, `xgboost==3.4.1`, `c2pa-python==0.38.0`, `torch`/`torchvision` (CPU build), `opencv-python-headless`, `pytesseract` + `tesseract-ocr` system binary) |
| torch / torchvision | CPU build of PyTorch — installable on Linux |
| OpenCV | `opencv-python-headless` — no GUI deps; system libraries (`libgl1`, `libglib2.0-0`) on some hosts |
| c2pa-python | Native C extensions; wheel exists for Linux — verify platform wheel in `requirements.txt` |
| Tesseract / OCR | `pytesseract` + `tesseract-ocr` system package. `TESSERACT_BIN` env var override. `tools/tessdata/` holds traineddata. |
| Torch model loading | `backend/app/ml/model_loader.py` loads from `MODELS_DIR`. `basirah-url-v3.joblib`, `detector_b_clip_probe.joblib`, `efficientnet_b0__C_holdout_Midjourney.pt` — runtime models shipped via Git LFS. |
| Upload handling | Temporary file handles; sanitized and inspected, no execution. `--reload` off for production. |

#### Linux blockers

None blocking. Required Linux packages: `tesseract-ocr` (and `tesseract-ocr-ara` for Arabic), `libgl1`/`libglib2.0-0` (OpenCV headless wheels may need them). `c2pa-python` wheels are provided for Linux x86_64; verify platform in `requirements.txt`.

### Tesseract portability

- `backend/app/content_intel.py` reads `TESSERACT_BIN` from environment, defaulting to the Windows path `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- Production behavior: if `TESSERACT_BIN` is set, it is used; otherwise the binary on `PATH` is used (Linux). The Windows default only affects local development on Windows.
- `tools/tessdata/` ships traineddata locally (`ara`, `eng`, `osd`) — used as `--tessdata-dir`.

### Git LFS preflight behavior

- `backend/app/ml/model_loader.py` loads models from `MODELS_DIR`. A model that is an LFS pointer (text beginning with `version https://git-lfs.github.com/spec/v1`) is not a pickle — `joblib.load()` will raise. The loader does not silently fall back to mock models; a missing/corrupt model degrades to the heuristic engine.
- Recommended startup preflight: assert each of the three LFS binaries exists and is non-empty; fail clearly if the file is a pointer text. Add a check in `app/metrics/production.py` or a `--health` startup step.

### Environment files

| File | Variables |
|---|---|
| `basirah/.env.example` | `VITE_API_BASE_URL=http://localhost:8000` (dev), production example `# VITE_API_BASE_URL=` (same-origin) |
| `backend/.env.example` | `BASIRAH_ENV`, `BASIRAH_CORS_ORIGINS`, `MODEL_DIR`, `TESSERACT_BIN` |

### Deployment files created

| File | Purpose |
|---|---|
| `.github/workflows/deploy-pages.yml` | GitHub Pages frontend deployment (produces `basirah/dist`) |
| `backend/.env.example` | Backend env template |
| `basirah/.env.example` | Frontend env template |

---

## 4. GitHub Pages workflow

- `.github/workflows/deploy-pages.yml` is committed, **enabled** but **disabled** until a backend URL is chosen.
- Workflow steps: checkout → setup Node 20 → `npm ci --no-audit --no-fund` → `npm run build` (with `VITE_API_BASE_URL` set) → `actions/configure-pages` → upload `basirah/dist` → `actions/deploy-pages`.
- No secrets are exposed. Production `VITE_API_BASE_URL` is added via a repository **variable** (not a secret): `VITE_API_BASE_URL=https://your-backend.example.com`.
- GitHub Pages **not enabled** yet, and no GitHub Pages **publish source** set — only after backend host selection.

---

## 5. Deployment target recommendation

### Primary host: Render

- Python 3.12 is supported.
- Free/Play tier is low-cost; auto-deploy from Git with `requirements.txt`.
- Git LFS is fetched automatically by Render during deploy.
- PyPI packages cover the stack (`torch`, `scikit-learn`, `xgpuboos`, `c2pa-python`, `opencv-python-headless`).
- `tesseract-ocr` is available via Render's apt/YAMl `env` (or a `systemDependencies` entry). Native component: `opencv-python-headless` wheels are GNU libc-linked (no GUI).
- **Caveat**: Render's free tier sleeps on inactivity. Production idle → cold start ~30–60 s. Credit is 750 hours/month. The `PORT` env var is auto-set by Render.

### Fallback host: Railway

- Python 3.12 supported, `PORT` auto-set, Git LFS supported.
- Free tier is limited; no forced sleeping on the free plan. Cold starts are similar to Render.
- Higher cost than the free Render tier; use if a persistent, always-on service is required.

### Why not Fly.io

- `opencv-python` needs system libraries (`libgl1`, `libglib2.0-0`, `libgomp1`); Fly.io's small VMs require a custom builder or a `Dockerfile` with `apt-get install`. The `build` step and `apt` run-time increase complexity.

---

## 6. Deployment order

1. Create backend host + publish `backend/.env.example` placeholders.
2. Confirm backend reaches `GET /health` on the externally reachable host.
3. Add `BASIRAH_CORS_ORIGINS=https://ish3-is.github.io` on the backend host.
4. Set GitHub Pages **publish source** to `basirah/dist` (from the workflow).
5. Enable GitHub Pages and verify www redirect + `/health` from GitHub Pages origin.
6. Set `VITE_API_BASE_URL` **repository variable** (no secret), push to trigger the workflow.
7. Verify the built `dist/` loads and calls the backend through the external origin.

---

## 7. Known limitations

- **No deployment performed in this stage.** GitHub Pages and backend hosting are left for the deployment operator.
- **No model performance claims** — images remain advisory/research-grade; no forensic certification.
- **No URL auto-browsing or file execution** — all analysis is string- or file-content-based.
- **OCR**: `pytesseract` + `tesseract-ocr` (Arabic `ara.traineddata` shipped). No EasyOCR in production.
- **C2PA**: import guarded; missing/malformed manifests yield `unavailable`.
- **No EXIF/ICC forensics** — only C2PA provenance is exposed.

---

## 8. Final status

**Deployment-ready for the frontend as static assets; backend deployment left for a separate Python-capable host. No deployment executed (not requested).**
