# BASIRAH — Deployment Readiness Report (Stage 4J)

> Purpose: audit deployment architecture. No deployment executed.

---

## 1. Frontend

| Concern | State |
|---|---|
| Artifact | `dist/` (static, built with `vite build`) |
| Base path | `'./'` — project-site deployable at any GitHub Pages path |
| Routing | SPA; served by the static host |
| Static asset paths | Hashed assets rewritten at build time |

## 2. Backend

| Concern | State |
|---|---|
| Artifact | `uvicorn app.main:app` (FastAPI, port 8000) |
| Hosting | Python-capable host only |

## 3. Known Constraint

**GitHub Pages serves static assets only and CANNOT host FastAPI.** The
frontend can be hosted on GitHub Pages, but the backend must be a separate
Python-capable host.

## 4. Strategy

| Deployment | Frontend | Backend |
|---|---|---|
| GitHub Pages frontend + external backend | GitHub Pages | Separate Python host |

Optional same-origin via reverse proxy: the Vite dev server proxies `/api`
to the backend (`changeOrigin: true`, `secure: false`). In production the
hosting stack must provide the same CORS handling.

## 5. Config Strategy

| File | Action |
|---|---|
| `vite.config.ts` | Already uses `base: './'` for project-site/path deployability |
| `.env.example` | Valid placeholder; set `VITE_API_BASE_URL` for the backend origin in dev |

---

## 6. Final Status

**Deployment-ready for the frontend as static assets; backend deployment
left for a separate Python-capable host. No deployment executed (not
requested).**
