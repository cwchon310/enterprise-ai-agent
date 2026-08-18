"""Integration tests. Use the rule LLM — no network, no API key needed."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

TEST_KEY = "test-secret"


def _make_settings(tmp_path) -> Settings:
    return Settings(
        api_key=TEST_KEY,
        llm_provider="rule",
        db_path=str(tmp_path / "test.db"),
    )


@pytest.fixture()
def client(tmp_path):
    # FastAPI's official override mechanism — replaces the captured dependency.
    app.dependency_overrides[get_settings] = lambda: _make_settings(tmp_path)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


AUTH = {"Authorization": f"Bearer {TEST_KEY}"}


def test_health_live(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_ready(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_query_requires_auth(client):
    r = client.post("/api/v1/query", json={"question": "hi"})
    assert r.status_code == 401


def test_query_wrong_key(client):
    r = client.post(
        "/api/v1/query",
        json={"question": "hi"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_ingest_then_query_roundtrip(client):
    ingest = client.post(
        "/api/v1/ingest",
        headers=AUTH,
        data={"namespace": "corp"},
        files={"file": ("manual.txt", "本公司 VPN 密碼係 1234，重啟要按重啟掣。".encode(), "text/plain")},
    )
    assert ingest.status_code == 201
    body = ingest.json()
    assert body["chunks"] >= 1
    assert body["namespace"] == "corp"

    q = client.post(
        "/api/v1/query",
        headers=AUTH,
        json={"question": "VPN 密碼係咩？", "namespace": "corp"},
    )
    assert q.status_code == 200
    data = q.json()
    assert data["provider"] == "rule"
    assert "VPN" in data["answer"] or "證據" in data["answer"]
    assert len(data["evidence"]) >= 1


def test_ingest_rejects_bad_extension(client):
    r = client.post(
        "/api/v1/ingest",
        headers=AUTH,
        files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
    )
    assert r.status_code == 400


def test_query_empty_namespace_defaults(client):
    ingest = client.post(
        "/api/v1/ingest",
        headers=AUTH,
        data={"namespace": "default"},
        files={"file": ("a.md", "# 標題\n伺服器 IP 係 10.0.0.5，端口 8080。".encode(), "text/plain")},
    )
    assert ingest.status_code == 201

    q = client.post(
        "/api/v1/query",
        headers=AUTH,
        json={"question": "伺服器端口幾多？"},
    )
    assert q.status_code == 200
    assert "8080" in q.json()["answer"]