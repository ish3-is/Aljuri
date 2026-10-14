# BASIRAH — URL Intelligence Engine (Phase 2)

Local, explainable URL analysis for BASIRAH | بصيرة.

A submitted URL is **parsed, never opened**. No page is fetched, no
JavaScript is executed, no external service is contacted, and no paid API
is used.

> **Advisory models.** BASIRAH ships three runtime ML models via Git LFS:
> `backend/models/basirah-url-v3.joblib`,
> `backend/models/detector_b_clip_probe.joblib`, and
> `backend/models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt`.
> Small metadata files (ACTIVE_MODEL.json, RESEARCH_IMAGE_MODEL.json,
> feature_schema.json) are tracked as normal Git text. No
> model-performance claims are made.

---

## Requirements

- Python 3.12 or newer (developed on 3.12.1)
- ~400 MB of packages

---

## Setup

Run these in PowerShell from the `backend` directory.

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## Running

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/health>

To run without activating the environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### Frontend

In a second terminal:

```powershell
cd D:\MDR\Aljuri-Greadute-Project\basirah
copy .env.example .env.local
npm run dev
```

The frontend calls `VITE_API_BASE_URL` (see `.env.example`). Restart the
dev server after changing it.

---

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

192 tests covering normalisation, feature extraction, entropy, all 18
heuristic rules, risk fusion, calibration properties, dataset handling and
the HTTP surface.

---

## Architecture

```
backend/
├── app/
│   ├── main.py                  FastAPI app, CORS
│   ├── api/routes.py            endpoints
│   ├── core/config.py           ALL thresholds, weights, lexicons
│   ├── schemas/                 request/response models
│   ├── services/
│   │   ├── url_analyzer.py      normalisation + security gate
│   │   ├── feature_extractor.py 41 deterministic features
│   │   ├── heuristic_engine.py  18 explainable rules
│   │   ├── risk_engine.py       fusion, banding, confidence
│   │   ├── explanation_engine.py evidence, DNA, timeline
│   │   └── analyzer.py          pipeline orchestration
│   └── ml/
│       ├── model_loader.py      load/save model bundle
│       ├── predictor.py         inference (honest unavailability)
│       └── dataset.py           CSV loading, label normalisation
├── models/                      trained artefacts (empty — see below)
├── datasets/                    README.md + dev fixture
├── docs/                        phase2-url-intelligence.md
├── scripts/
│   ├── train_url_model.py
│   └── evaluate_url_model.py
└── tests/
```

Full design rationale, feature definitions, rule weights and the risk
fusion method: **`../docs/phase2-url-intelligence.md`**.

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status, rule count, feature count, model availability |
| `POST` | `/api/analyze/url` | Analyse one URL |
| `GET` | `/api/model/info` | Model transparency metadata (no filesystem paths) |
| `GET` | `/health` | Liveness alias |

### Example

```powershell
curl.exe -X POST http://localhost:8000/api/analyze/url `
  -H "Content-Type: application/json" `
  -d '{\"url\": \"https://example.com\"}'
```

Accepted inputs: `example.com`, `www.example.com`,
`https://example.com`, `http://example.com/login`.

Rejected with HTTP 422: `javascript:`, `file://`, `data:`, `ftp://`, and
URLs over 2048 characters.

---

## Security posture

| Property | Implementation |
|---|---|
| No URL fetching | Analysis is string-only; nothing is dereferenced |
| No JavaScript execution | Nothing is rendered or scripted |
| Scheme allow-list | `http`, `https` only, gated before parsing |
| Input size limit | 2048 characters, enforced twice (Pydantic + normaliser) |
| No shell interpolation | Submitted values never reach a subprocess |
| Offline operation | `tldextract` uses its bundled suffix snapshot, no network |
| CORS | Explicit development origins; wildcard never used |
| Path disclosure | `/api/model/info` exposes no filesystem paths |
| Corpus integrity | A test asserts no model artefact is committed |

---

## Training a model

### Dataset format

CSV with `url` and `label` columns. Full documentation, including
accepted column-name and label-vocabulary variations, is in
`datasets/README.md`.

Labels are normalised from any of:

- phishing: `1`, `true`, `yes`, `phishing`, `malicious`, `bad`, `fraud`
- benign: `0`, `false`, `no`, `legit`, `legitimate`, `benign`, `good`, `safe`

An unrecognised label **raises an error** rather than being coerced,
because silently defaulting to `0` would poison the training set.

### Commands

```powershell
# Evaluate whatever is currently trained
.\.venv\Scripts\python.exe -m scripts.evaluate_url_model

# Train on a real dataset
.\.venv\Scripts\python.exe -m scripts.train_url_model --data datasets\<your-file>.csv
```

Selection rule: **maximum F1, ties broken by recall.** Accuracy is
reported but never used for selection — on an imbalanced split a model
that never predicts phishing scores highly on accuracy alone.

Leakage controls: stratified split, scaling inside the pipeline (fitted on
the training fold only), duplicates removed before splitting,
`random_state = 42`.

### The development fixture

`datasets/dev_fixture_urls.csv` holds 20 hand-written rows whose only
purpose is to prove the pipeline runs.

The trainer **refuses it** unless you pass `--allow-dev-fixture`, and then
marks the resulting model `evaluated: false` with a warning. On those 20
rows every model scores 1.0000 — which is exactly why such a result must
never be reported as evidence of anything.

---

## Model files

A trained bundle produces two files in `models/`:

| File | Contents |
|---|---|
| `url_risk_model.joblib` | Estimator, bundle version, feature order |
| `url_risk_model.metadata.json` | Model name, dataset provenance, metrics, selection rule |

The feature order is persisted with the model and re-verified at load. If
the extractor changes after training, inference is **skipped** with an
explanatory reason rather than silently misaligned.

---

## Configuration

All tunables live in `app/core/config.py` — weights, thresholds, lexicons.
Override via environment variables or a `.env` file (see `Settings`).

Nothing in this project is secret. There are no API keys.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Frontend shows "analysis service is unavailable" | Backend not running, or `VITE_API_BASE_URL` wrong |
| Frontend ignores a `.env` change | Restart the Vite dev server |
| `ModuleNotFoundError: fastapi` | Wrong interpreter — use `.\.venv\Scripts\python.exe` |
| Port already in use | `uvicorn ... --port 8001`, and update `.env.local` |
| CORS error in the browser console | Add the origin to `cors_origins` in `app/core/config.py` |

---

## Reference

- Design rationale, features, rules, fusion method, evaluation plan and
  limitations: `../docs/phase2-url-intelligence.md`
