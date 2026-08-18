"""Query endpoint: RAG question answering."""

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.schemas import Evidence, QueryRequest, QueryResponse
from app.services.agent import run_agent
from app.services.llm import build_llm
from app.services.storage import DocumentStore

router = APIRouter(tags=["query"])


def get_store(settings: Settings = Depends(get_settings)) -> DocumentStore:
    from app.main import app_state

    return app_state.store


@router.post("", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    settings: Settings = Depends(get_settings),
    store: DocumentStore = Depends(get_store),
) -> QueryResponse:
    llm = build_llm(settings)
    try:
        answer, evidence_rows, trace = run_agent(
            llm=llm,
            store=store,
            question=payload.question,
            namespace=payload.namespace,
            settings=settings,
            use_tools=payload.use_tools,
        )
    except Exception as exc:  # noqa: BLE001 - surface LLM/network errors cleanly
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc

    return QueryResponse(
        answer=answer,
        provider=llm.provider,
        model=getattr(llm, "model", settings.llm_provider),
        evidence=[
            Evidence(chunk_id=cid, content=content, score=score)
            for cid, content, score in evidence_rows
        ],
        raw=trace,
    )