"""
BASIRAH — URL Intelligence Engine (Phase 2).

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Local, explainable URL intelligence for BASIRAH. "
        "Analysis is derived entirely from the submitted URL string: "
        "no page is fetched, no JavaScript is executed, and no external "
        "service is contacted."
    ),
)

# CORS is restricted to explicit development origins. A production
# GitHub Pages origin must be added to settings.cors_origins explicitly;
# wildcard credentials are never enabled.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)


# Liveness at the root, so `GET /` is meaningful without knowing the
# API prefix. Registered outside the /api router to keep the public
# surface at exactly four endpoints.
_root_router = APIRouter(tags=["system"])


@_root_router.get("/health", include_in_schema=False)
def _health_alias() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


app.include_router(_root_router)
