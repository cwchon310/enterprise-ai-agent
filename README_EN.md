# Enterprise AI Agent Platform

> Enterprise-grade RAG + Agent platform — an AI knowledge-base Q&A system you can run on your own Mac or a company server. Supports **multiple LLM providers** (DeepSeek / OpenAI / local Ollama), **Retrieval-Augmented Generation (RAG)**, document indexing, and enterprise-grade design (layered architecture, Docker, CI, tests, API-key auth, structured logging).

**🌐 Language:** [中文](README.md) | English

![System Architecture](docs/architecture.png)

---

## Features

| Feature | Description |
|---------|-------------|
| 📄 **Document ingestion** | Upload Markdown / TXT / PDF; auto-split and index |
| 🔍 **Retrieval-Augmented Generation** | SQLite FTS5 full-text search (zero external deps) + optional embedding vector search |
| 🤖 **Multi-LLM support** | DeepSeek / OpenAI / Ollama (local) / no-key rule-engine fallback |
| 🧠 **Agent loop** | System prompt + tool calling (tools: retrieval, current time, arithmetic) |
| 🔐 **API-key auth** | Enterprise-grade Bearer Token protecting every endpoint |
| 📝 **Structured logging** | JSON logs, ready for Loki / ELK |
| 🐳 **Containerized** | Dockerfile + docker-compose, one command to start |
| ✅ **Tests** | pytest unit + integration tests (no real LLM needed) |
| ⚙️ **CI** | GitHub Actions: lint + test + build |

---

## Quick Start

### 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Start the server

```bash
# Works without any LLM key (rule engine — try the whole flow for free)
uvicorn app.main:app --reload --port 8000

# Or with Docker (enterprise deployment)
docker compose up --build
```

### 3. Use it

```bash
# Set the API key (inside .env)
export AGENT_API_KEY=dev-secret-key

# Upload a document (build the index)
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer dev-secret-key" \
  -F "file=@README.md" \
  -F "namespace=support"

# Ask a question (RAG answer)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question":"What can this platform do?","namespace":"support"}'
```

Interactive docs (OpenAPI): <http://localhost:8000/docs>

---

## Architecture

```
                        ┌─────────────────────┐
                        │      Client         │
                        │ (curl / App / Web)  │
                        └──────────┬──────────┘
                                   │ Bearer Token
                                   ▼
┌──────────────────────────────────────────────────────────┐
│                     FastAPI (ASGI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Logging  │ │ Auth     │ │ Routers  │ │ Middleware  │  │
│  │ (JSON)   │ │ (Bearer) │ │ v1       │ │ (CORS/GZip) │  │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────┘  │
└──────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  ┌───────────────┐        ┌───────────────┐         ┌────────────────┐
  │   Ingestion   │        │   Retrieval   │         │   Agent / LLM  │
  │ Service       │        │ Service       │         │ Service        │
  │ - chunk/clean │        │ - FTS5 search │         │ - provider abs │
  │ - store SQLite│        │ - rank/filter │         │ - tool calling │
  └───────────────┘        └───────────────┘         └────────────────┘
         │                         │                          │
         ▼                         ▼                          ▼
  ┌───────────────────────────────────────────────────────┐
  │              SQLite (documents + chunks + FTS5)       │
  └───────────────────────────────────────────────────────┘
```

**Design principles:** clean layering (Router → Service → Repository), each layer independently testable; every external dependency (LLM) goes through an abstract interface, so swapping providers never touches core logic.

---

## Project Structure

```
enterprise-ai-agent/
├── app/
│   ├── main.py            # FastAPI entry (lifespan, CORS, route mounting)
│   ├── config.py          # settings (pydantic-settings, reads .env)
│   ├── models/
│   │   └── schemas.py     # Pydantic request/response models
│   ├── routers/
│   │   ├── health.py      # /health liveness + readiness probes
│   │   ├── ingest.py      # /ingest document upload → index
│   │   └── query.py       # /query Q&A (RAG)
│   ├── services/
│   │   ├── ingestion.py   # document chunking, cleaning, SQLite writes
│   │   ├── retrieval.py   # FTS5 search + rerank
│   │   ├── llm.py         # LLM provider abstraction (DeepSeek/OpenAI/Ollama/Rule)
│   │   └── agent.py       # agent loop (prompting + tool calling)
│   └── middleware/
│       └── logging.py     # JSON structured request logging
├── scripts/
│   └── generate_diagram.py   # draws the architecture diagram with PIL (docs/architecture.png)
├── tests/
│   └── test_api.py        # pytest integration tests
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── Makefile
└── README.md
```

---

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_API_KEY` | `dev-secret-key` | Client API key (use a strong one in production) |
| `LLM_PROVIDER` | `rule` | `deepseek` / `openai` / `ollama` / `rule` |
| `DEEPSEEK_API_KEY` | - | DeepSeek key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API endpoint |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek model name |
| `OPENAI_API_KEY` | - | OpenAI key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Ollama model name |
| `DB_PATH` | `agent.db` | SQLite file location |
| `CORS_ORIGINS` | `*` | Allowed origins (comma-separated) |

---

## Tests

```bash
pytest -v
```

Tests use a **fake LLM** — no network, no key, runs straight in CI.

---

## Deployment

### Docker (recommended)

```bash
docker compose up --build -d
# verify health
curl http://localhost:8000/health/live
```

### Manual (systemd example)

```ini
[Unit]
Description=Enterprise AI Agent
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/enterprise-ai-agent
ExecStart=/opt/enterprise-ai-agent/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## FAQ

**Q: How do I try it without an LLM key?**
A: Use the default `rule` provider — the engine returns "retrieved evidence + answer" directly and runs the whole RAG flow for you. Great for a quick demo.

**Q: Does it support PDFs?**
A: Yes. `ingestion.py` auto-detects the file extension; PDFs use `pypdf` to extract text (requires `pip install pypdf`).

**Q: How do I add another LLM?**
A: Add a new Provider class in `services/llm.py` (subclass `BaseLLM`) — a few dozen lines, done.

**Q: How do I enable embedding vector search?**
A: It needs `sentence-transformers` (downloads a model). Once enabled, the engine merges FTS5 + vector results for higher accuracy. Off by default because it downloads a model.

---

## License

MIT License