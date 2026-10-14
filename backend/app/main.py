"""
BASIRAH — URL Intelligence Engine (Phase 2).

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.ml.model_readiness import policy_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup validation for mandatory runtime models.

    BASIRAH uses STRICT_STARTUP for its three runtime-required models:
    if any model is missing, zero-byte, still a Git LFS pointer, or
    otherwise unreadable, the service fails to start with a clear error
    instead of booting with a broken model.

    This is the deployment-safe behavior. In production the models are
    shipped via Git LFS and the preflight passes; this is a defensive gate
    that protects against a bad build artefact.
    """
    allowed, reason = policy_check()
    if not allowed:
        print(
            "FATAL: BASIRAH startup blocked — runtime model preflight failed: "
            f"{reason}",
            file=sys.stderr,
        )
        print(
            "FATAL: Run `git lfs pull` and reinstall if the models are "
            "missing or still LFS pointers.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("BASIRAH startup: runtime model preflight passed.", flush=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Local, explainable URL intelligence for BASIRAH. "
        "Analysis is derived entirely from the submitted URL string: "
        "no page is fetched, no JavaScript is executed, and no external "
        "service is contacted."
    ),
    lifespan=lifespan,
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
