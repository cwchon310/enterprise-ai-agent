"""FastAPI application entry point."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import Settings, get_settings
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import health, ingest, query
from app.services.storage import DocumentStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@dataclass
class AppState:
    store: DocumentStore


app_state: AppState | None = None


def resolve_settings() -> Settings:
    """Return the overridden settings when tests install one, else the real one."""
    override = app.dependency_overrides.get(get_settings)
    return override() if override else get_settings()


def require_api_key(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Bearer token guard for all /api/v1 endpoints."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    expected = f"{settings.token_prefix}{settings.api_key}"
    if authorization.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_state
    # Resolve through the override table so tests can isolate their DB.
    settings = resolve_settings()
    app_state = AppState(store=DocumentStore(settings.db_path, settings.top_k))
    logging.getLogger("access").setLevel(settings.log_level.upper())
    yield
    app_state.store.close()


app = FastAPI(
    title="Enterprise AI Agent Platform",
    version="1.0.0",
    description="企業級 RAG + Agent 平台：文件索引、全文檢索、多 LLM 問答。",
    lifespan=lifespan,
)

# Middleware order: request logging outermost, then CORS, then gzip.
app.add_middleware(RequestLoggingMiddleware)
origins = [o.strip() for o in get_settings().cors_origins.split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health.router, prefix="/health")
app.include_router(ingest.router, prefix="/api/v1/ingest", dependencies=[Depends(require_api_key)])
app.include_router(query.router, prefix="/api/v1/query", dependencies=[Depends(require_api_key)])


@app.get("/")
def root() -> dict:
    return {"service": "enterprise-ai-agent", "docs": "/docs", "health": "/health/live"}