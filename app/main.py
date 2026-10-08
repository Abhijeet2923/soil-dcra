"""
SoilDCRA — AI-Driven Soil Degradation Assessment & Multi-Season Crop Rotation
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db
from app.data.seed import run_seed
from app.api.v1 import fields, soil, analysis, optimization

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Decision-support prototype for soil health assessment "
        "and CP-SAT-driven multi-season crop rotation optimisation. "
        "All outputs are illustrative and require expert validation."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initialise database tables and seed demo data."""
    init_db()
    run_seed()


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(fields.router,       prefix=PREFIX)
app.include_router(soil.router,         prefix=PREFIX)
app.include_router(analysis.router,     prefix=PREFIX)
app.include_router(optimization.router, prefix=PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get(f"{PREFIX}/health", tags=["health"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}
