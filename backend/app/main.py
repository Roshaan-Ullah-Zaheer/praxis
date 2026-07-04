"""Praxis API entry point.

A governed multi-agent document intelligence workspace. This module wires up the
FastAPI app, CORS for the frontend, and the health/readiness endpoints. Feature
routers (documents, conversations, governance, billing) are mounted as each
milestone lands.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .api import billing, conversations, documents, governance, sample

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Praxis API",
    description="Governed multi-agent document intelligence workspace.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(governance.router, prefix="/api")
app.include_router(sample.router, prefix="/api")
app.include_router(billing.router, prefix="/api")


@app.get("/", tags=["meta"])
def root() -> dict:
    """Service banner with pointers to docs and health."""
    return {"name": "Praxis", "status": "running", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness + readiness probe (also the keep-warm ping target)."""
    return {
        "status": "ok",
        "service": "praxis",
        "providers_configured": config.providers_configured(),
    }
