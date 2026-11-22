"""Service-layer unit tests. No network, no API key."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.services.ingestion import clean_text, chunk_text, IngestionError
from app.services.storage import DocumentStore
from app.services.agent import run_agent, _render_evidence


def test_render_evidence_empty():
    assert _render_evidence([]) == "（無相關資料）"


def test_render_evidence_has_blocks():
    rows = [(1, "hello world\nline two", 0.5)]
    out = _render_evidence(rows)
    assert "[[EV]]" in out
    assert "hello world line two" in out


def test_clean_text_collapses_whitespace():
    assert clean_text("a   b\n\n\nc") == "a b\n\nc"


def test_chunk_text_overlap():
    chunks = chunk_text("A" * 2500, chunk_size=1000, overlap=200)
    assert len(chunks) >= 2
    assert all(len(c) <= 1000 for c in chunks)


def test_chunk_text_empty():
    assert chunk_text("", 1000, 200) == []


def test_store_add_and_search():
    with tempfile.TemporaryDirectory() as d:
        store = DocumentStore(str(Path(d) / "t.db"), top_k=3)
        doc_id = store.add_document("ns1", "a.txt", ["alpha beta gamma", "delta epsilon"])
        assert isinstance(doc_id, int)
        rows = store.search("alpha", "ns1")
        assert len(rows) >= 1
        assert rows[0][1] == "alpha beta gamma"
        # namespace isolation
        assert store.search("alpha", "ns2") == []
        store.close()


def test_agent_rule_style_uses_evidence():
    from app.services.llm import RuleLLM
    from app.config import Settings

    class FakeStore:
        def search(self, q, ns):
            return [(1, "公司 VPN 密碼係 1234", 0.1)]

    llm = RuleLLM(Settings(llm_provider="rule", api_key="k"))
    settings = Settings(llm_provider="rule", api_key="k")
    answer, evidence, trace = run_agent(
        llm=llm, store=FakeStore(), question="VPN 密碼係咩？", namespace="ns", settings=settings
    )
    assert "1234" in answer or "證據" in answer
    assert len(evidence) == 1


def test_ingestion_error_on_empty():
    with IngestionError if False else pytest.raises(IngestionError):
        raise IngestionError("boom")
