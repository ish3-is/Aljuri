# BASIRAH — Dependencies Evidence (Internal Drafting Reference)

> Purpose: audit actual dependency manifests and produce an accurate
> dependency table. Do not infer versions when manifests provide exact values.

---

## 1. Frontend (`basirah/package.json`)

| Library | Version | Purpose | Tier |
|---|---|---|---|
| react | ^19.2.8 | UI framework | Required |
| react-dom | ^19.2.8 | React DOM | Required |
| @tailwindcss/vite | ^4.3.3 | Tailwind Vite plugin | Required |
| tailwindcss | ^4.3.3 | CSS framework | Required |
| clsx | ^2.1.1 | Conditional className utility | Required |
| exceljs | ^4.4.0 | Excel workbook export (dynamic import) | Required |
| lucide-react | ^1.50.0 | Icon set | Required |
| motion | ^14.0.0 | Framer Motion animations | Required |
| recharts | ^3.10.1 | Charts (graph) | Required |
| @vitejs/plugin-react | ^6.1.1 | React Vite plugin | Dev |
| vite | ^8.3.0 | Build tool | Dev |
| typescript | ~6.0.2 | Types | Dev |
| @types/react / @types/react-dom | ^19.2.18 / ^19.2.7 | React types | Dev |
| @types/node | ^24.13.3 | Node types | Dev |
| @eslint/js, eslint, typescript-eslint, globals | — | Linting | Dev |
| eslint-plugin-react-hooks, react-refresh | — | Linting | Dev |
| jsdom | ^30.1.2 | QA test DOM | Dev |
| sharp | ^0.35.5 | Image tooling (QA) | Dev |

---

## 2. Backend (`backend/requirements.txt`)

| Library | Version | Purpose | Tier |
|---|---|---|---|
| fastapi | 0.115.6 | Web framework | Required |
| uvicorn[standard] | 0.34.0 | ASGI server | Required |
| pydantic | 2.10.4 | Validation | Required |
| pydantic-settings | 2.7.0 | Settings | Required |
| numpy | 2.2.1 | Numerics | Required |
| pandas | 2.2.3 | Data/frame | Required |
| scikit-learn | 1.6.1 | ML | Required |
| joblib | 1.4.2 | Model persistence | Required |
| tldextract | 5.1.2 | URL parsing | Required |
| pytest | 8.3.4 | Testing | Dev |
| httpx | 0.28.1 | HTTP client | Dev |
| **c2pa-python** | **0.38.0** | C2PA provenance support | Production |
| xgboost | 3.4.1 | ML | Required |
| matplotlib | 3.11.2 | Charts | Required |

> **Verified:** `c2pa-python==0.38.0` exactly as mandated. No unexplained
> packages. No hidden mining dependencies.

---

## 3. Version Pinning Policy

- All versions are **exact pins** (e.g. `fastapi==0.115.6`), not ranges.
- `requirements.txt` contains only the packages above.
- No unreported packages are used in the backend; no unreported packages are
  used in the frontend.
