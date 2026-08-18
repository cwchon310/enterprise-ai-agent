"""Pydantic request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4096)
    namespace: str = Field(default="default", min_length=1, max_length=128)
    use_tools: bool = True


class Evidence(BaseModel):
    chunk_id: int
    content: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    provider: str
    model: str
    evidence: list[Evidence] = []
    raw: dict[str, Any] = {}


class IngestResponse(BaseModel):
    document_id: int
    filename: str
    chunks: int
    namespace: str