"""Ingestion endpoint: upload a file, index it."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.models.schemas import IngestResponse
from app.services.ingestion import IngestionError, chunk_text, clean_text, extract_text
from app.services.storage import DocumentStore

router = APIRouter(tags=["ingest"])


def get_store(settings: Settings = Depends(get_settings)) -> DocumentStore:
    from app.main import app_state

    return app_state.store


@router.post("", response_model=IngestResponse, status_code=201)
async def ingest_document(
    file: UploadFile,
    namespace: str = Form("default"),
    settings: Settings = Depends(get_settings),
    store: DocumentStore = Depends(get_store),
) -> IngestResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    try:
        raw = extract_text(file.filename, file.file)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cleaned = clean_text(raw)
    if not cleaned:
        raise HTTPException(status_code=400, detail="No extractable text")

    chunks = chunk_text(cleaned, settings.chunk_size, settings.chunk_overlap)
    doc_id = store.add_document(namespace, file.filename, chunks)
    return IngestResponse(
        document_id=doc_id,
        filename=file.filename,
        chunks=len(chunks),
        namespace=namespace,
    )