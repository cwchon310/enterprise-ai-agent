# 架構深度解析

本文詳細拆解 Enterprise AI Agent Platform 的內部架構、數據流與擴展點。

## 整體分層

```
┌─────────────────────────────────────────────────────────────┐
│                      API 層（FastAPI Routers）               │
│  /health  /ingest  /query  /admin                            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    服務層（Services）                         │
│  Ingestion → Retrieval → LLM → Agent                         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    儲存層（SQLite + FTS5）                    │
│  documents / chunks / fts5_index                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 資料流：Ingest（建索引）

```
用戶上傳檔案
    │
    ▼
┌─────────────┐
│  Routers    │  /api/v1/ingest （multipart upload）
└─────────────┘
    │
    ▼
┌─────────────┐
│ Ingestion   │  1. 偵測副檔名（md/txt/pdf）
│ Service     │  2. 抽取文字（pypdf / 純文字）
│             │  3. 切分（chunking，預設 500 字）
│             │  4. 寫入 SQLite (documents + chunks)
│             │  5. 建 FTS5 全文索引
└─────────────┘
    │
    ▼
┌─────────────┐
│  SQLite     │  持久化儲存
└─────────────┘
```

### 關鍵程式碼

```python
# app/services/ingestion.py
async def ingest_file(file, namespace: str):
    text = extract_text(file)           # md / txt / pdf
    chunks = split_text(text, size=500) # 切分
    for chunk in chunks:
        db.execute(
            "INSERT INTO chunks (namespace, content) VALUES (?, ?)",
            (namespace, chunk),
        )
    db.execute(
        "INSERT INTO fts_chunks (content) VALUES (?)",
        (chunk,),
    )
```

---

## 資料流：Query（RAG 問答）

```
用戶提問
    │
    ▼
┌─────────────┐
│  Routers    │  /api/v1/query（JSON body）
└─────────────┘
    │
    ▼
┌─────────────┐
│ Retrieval   │  1. FTS5 全文檢索
│ Service     │  2. （可選）Embedding 向量檢索
│             │  3. 重排 + 取 Top-K
└─────────────┘
    │
    ▼
┌─────────────┐
│  LLM        │  DeepSeek / OpenAI / Ollama / Rule
│ Service     │  4. 組建 Prompt（證據 + 問題）
└─────────────┘
    │
    ▼
┌─────────────┐
│  Agent      │  5. 工具調用（檢索 / 時間 / 計算）
└─────────────┘
    │
    ▼
回答給用戶
```

---

## LLM Provider 抽象

所有 LLM 呼叫都經過 `BaseLLM` 介面，換供應商不用動核心邏輯：

```python
# app/services/llm.py
class BaseLLM:
    async def complete(self, prompt: str) -> str: ...

class DeepSeekLLM(BaseLLM): ...
class OpenAILLM(BaseLLM): ...
class OllamaLLM(BaseLLM): ...
class RuleLLM(BaseLLM):   # 無 Key fallback
```

設定 `LLM_PROVIDER` 即切換，見 `.env.example`。

---

## Agent 工具循環

Agent 支援三種內建工具，可透過 `services/agent.py` 擴充：

| 工具 | 用途 | 例子 |
|------|------|------|
| `retrieve` | 從向量/全文索引檢索證據 | 「查詢公司假期政策」 |
| `now` | 取得現時時間 | 「現在幾點？」 |
| `calculate` | 簡單數學運算 | 「123 * 456 等於幾？」 |

---

## 擴展指南

### 加入新 LLM Provider

1. 在 `app/services/llm.py` 新建 class 繼承 `BaseLLM`
2. 實作 `complete()` 方法
3. 在 `config.py` / `.env` 新增對應環境變數
4. 在工廠函數裡註冊新 provider

### 加入新 Agent 工具

1. 在 `app/services/agent.py` 新增工具 function
2. 註冊到 `TOOLS` 字典
3. 更新系統提示詞，讓 Agent 知道何時呼叫

### 向量檢索（可選）

安裝 `sentence-transformers` 後，在 `Retrieval Service` 開啟向量路徑，與 FTS5 結果合併再重排，準確度會更高。

---

## 效能與擴展性

| 項目 | 說明 |
|------|------|
| 資料庫 | SQLite 單檔，適合單機／小團隊；大規模可換 PostgreSQL |
| 併發 | FastAPI + uvicorn，建議 Docker 加 `--workers 2` |
| 快取 | 可加 Redis 快取常見查詢結果 |
| 監控 | JSON 結構化日誌，可接 Loki / ELK |
