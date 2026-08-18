"""Document ingestion: extraction, cleaning, chunking."""

from __future__ import annotations

import re
from typing import BinaryIO

from app.config import Settings


class IngestionError(Exception):
    pass


def _read_markdown(stream: BinaryIO) -> str:
    return stream.read().decode("utf-8", errors="replace")


def _read_pdf(stream: BinaryIO) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise IngestionError("PDF support needs: pip install pypdf") from None
    reader = PdfReader(stream)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_text(filename: str, stream: BinaryIO) -> str:
    """Route file to the right extractor by extension."""
    lower = filename.lower()
    if lower.endswith((".md", ".txt", ".markdown")):
        return _read_markdown(stream)
    if lower.endswith(".pdf"):
        return _read_pdf(stream)
    raise IngestionError(f"Unsupported file type: {filename}")


def clean_text(text: str) -> str:
    """Normalise whitespace / control chars for better chunking & search."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks on paragraph / newline boundaries."""
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) <= chunk_size:
            buf = f"{buf}\n\n{para}".strip() if buf else para
            continue
        if buf:
            chunks.append(buf)
            buf = ""
        # paragraph longer than chunk_size: hard split
        while len(para) > chunk_size:
            chunks.append(para[:chunk_size])
            para = para[chunk_size - overlap :]
        buf = para
    if buf:
        chunks.append(buf)
    return chunks


def ingest_file(
    filename: str, stream: BinaryIO, settings: Settings
) -> tuple[int, list[str]]:
    """Full pipeline: extract -> clean -> chunk. Returns (doc_id, chunks)."""
    raw = extract_text(filename, stream)
    cleaned = clean_text(raw)
    if not cleaned:
        raise IngestionError("No extractable text in file")
    return cleaned, chunk_text(cleaned, settings.chunk_size, settings.chunk_overlap)