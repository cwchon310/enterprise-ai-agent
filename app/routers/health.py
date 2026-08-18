"""Health endpoints: liveness + readiness."""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.schemas import HealthResponse
from app.services.storage import DocumentStore

router = APIRouter(tags=["health"])


def get_store(settings: Settings = Depends(get_settings)) -> DocumentStore:
    from app.main import app_state

    return app_state.store


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


@router.get("/ready", response_model=HealthResponse)
def readiness(store: DocumentStore = Depends(get_store)) -> HealthResponse:
    # A real readiness probe touches storage so load balancers route correctly.
    store.count_documents()
    return HealthResponse(status="ready", version="1.0.0")