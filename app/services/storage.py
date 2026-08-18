"""Database layer (repository). SQLite + FTS5, zero external deps."""

from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path

from app.config import Settings


class DocumentStore:
    """Thin repository around SQLite. One writer connection + WAL mode."""

    def __init__(self, db_path: str, top_k: int = 5) -> None:
        self._path = Path(db_path)
        self._lock = threading.Lock()
        self._top_k = top_k
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    content, content='chunks', content_rowid='id'
                );
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
                END;
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
                END;
                """
            )
            self._conn.commit()

    def add_document(self, namespace: str, filename: str, chunks: list[str]) -> int:
        """Insert a document + its chunks. Returns document id."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO documents(namespace, filename) VALUES (?, ?)",
                (namespace, filename),
            )
            doc_id = cur.lastrowid
            self._conn.executemany(
                "INSERT INTO chunks(document_id, content, position) VALUES (?, ?, ?)",
                [(doc_id, c, i) for i, c in enumerate(chunks)],
            )
            self._conn.commit()
            return doc_id

    def search(self, query: str, namespace: str) -> list[tuple[int, str, float]]:
        """BM25 full-text search scoped to a namespace. Returns (chunk_id, content, score)."""
        # FTS5 cannot filter by namespace directly, so join back to documents.
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT c.id, c.content, bm25(chunks_fts) AS score
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                JOIN documents d ON d.id = c.document_id
                WHERE chunks_fts MATCH ? AND d.namespace = ?
                ORDER BY score
                LIMIT ?
                """,
                (self._safe_query(query), namespace, self._top_k),
            ).fetchall()
            return [(r["id"], r["content"], float(r["score"])) for r in rows]

    @staticmethod
    def _safe_query(raw: str) -> str:
        """Build a lenient FTS5 query: english tokens whole, CJK as bigrams.

        FTS5's unicode61 tokenizer treats a run of CJK chars as ONE token, so a
        phrase search can never match. Splitting CJK into bigrams makes Chinese
        search actually work while keeping the query injection-safe.
        """
        cleaned = raw.strip().replace('"', " ")
        tokens = re.findall(r"[a-zA-Z0-9_]{2,}", cleaned)
        for block in re.findall(r"[\u4e00-\u9fff]+", cleaned):
            if len(block) == 1:
                tokens.append(block)
            else:
                tokens.extend(block[i : i + 2] for i in range(len(block) - 1))
        if not tokens:
            return f'"{cleaned}"'
        return " OR ".join(f'"{t}"' for t in tokens[:10])

    def count_documents(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()