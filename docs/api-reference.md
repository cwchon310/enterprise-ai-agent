# API 參考

Base URL：`http://localhost:8000/api/v1`

所有受保護端點需要 `Authorization: Bearer <AGENT_API_KEY>`。

---

## POST /ingest

上傳文件並建立索引。

### 請求

```
Content-Type: multipart/form-data

file: <File>        # 必需，支援 .md / .txt / .pdf
namespace: <String> # 必需，命名空間，用於隔離不同資料
```

### 回應

```json
{
  "status": "ok",
  "chunks_indexed": 42,
  "namespace": "support"
}
```

### 範例

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer dev-secret-key" \
  -F "file=@README.md" \
  -F "namespace=support"
```

---

## POST /query

RAG 問答，根據問題檢索相關文件並生成回答。

### 請求

```json
{
  "question": "公司假期政策是什麼？",
  "namespace": "support",
  "top_k": 5
}
```

| 欄位 | 類型 | 必需 | 說明 |
|------|------|------|------|
| `question` | string | ✅ | 使用者問題 |
| `namespace` | string | ✅ | 檢索範圍 |
| `top_k` | int | ❌ | 返回檢索片段數量，預設 5 |

### 回應

```json
{
  "answer": "根據文件，員工每年享有 14 天年假...",
  "sources": [
    {
      "content": "...",
      "score": 0.85
    }
  ]
}
```

### 範例

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question":"呢個平台有咩功能？","namespace":"support"}'
```

---

## GET /health/live

存活檢查，無需認證。

```bash
curl http://localhost:8000/health/live
# 回應: {"status": "alive"}
```

## GET /health/ready

就緒檢查，確認資料庫可用。

```bash
curl http://localhost:8000/health/ready
# 回應: {"status": "ready"}
```

---

## OpenAPI 文件

啟動伺服器後，瀏覽器開啟：

```
http://localhost:8000/docs
```
