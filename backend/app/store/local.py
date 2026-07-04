"""Local zero-infra storage backend.

SQLite (with FTS5 for keyword search) for all metadata + an embedding column
that NumPy reads back for cosine similarity. Originals live on the local
filesystem. Good for development and the free public demo; the same interface is
implemented over Postgres + pgvector for production.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

import numpy as np

from .base import ChunkRecord, DocumentRecord, RetrievedChunk, Store

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    filename    TEXT NOT NULL,
    mime        TEXT NOT NULL,
    size        INTEGER NOT NULL,
    page_count  INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'queued',
    file_hash   TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS document_roles (
    document_id TEXT NOT NULL,
    role        TEXT NOT NULL,
    PRIMARY KEY (document_id, role)
);
CREATE TABLE IF NOT EXISTS chunks (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    page        INTEGER NOT NULL,
    ordinal     INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    content     TEXT NOT NULL,
    embedding   TEXT,
    token_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content, chunk_id UNINDEXED, document_id UNINDEXED
);
CREATE TABLE IF NOT EXISTS embedding_cache (
    content_hash TEXT PRIMARY KEY,
    embedding    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT 'New conversation',
    active_role TEXT,
    summary     TEXT NOT NULL DEFAULT '',
    working_set TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    strategy        TEXT,
    grounding       TEXT,
    confidence      REAL,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS message_sources (
    message_id  TEXT NOT NULL,
    chunk_id    TEXT NOT NULL,
    document_id TEXT NOT NULL,
    page        INTEGER NOT NULL,
    snippet     TEXT NOT NULL,
    rank        INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT,
    message_id      TEXT,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    target          TEXT NOT NULL DEFAULT '',
    role_context    TEXT,
    ts              TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subscriptions (
    owner_id             TEXT PRIMARY KEY,
    tier                 TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id   TEXT,
    stripe_subscription_id TEXT,
    status               TEXT NOT NULL DEFAULT 'active',
    current_period_end   TEXT
);
CREATE TABLE IF NOT EXISTS query_cache (
    key        TEXT PRIMARY KEY,
    answer     TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalStore(Store):
    def __init__(self, data_dir: str) -> None:
        self.data_dir = os.path.abspath(data_dir)
        self.files_dir = os.path.join(self.data_dir, "files")
        os.makedirs(self.files_dir, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(
            os.path.join(self.data_dir, "praxis.db"), check_same_thread=False
        )
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.commit()

    # ── Documents ────────────────────────────────────────────────────────────
    def create_document(
        self, owner_id, filename, mime, size, file_hash, storage_path, status="queued"
    ) -> str:
        doc_id = uuid.uuid4().hex
        with self._lock:
            self._db.execute(
                "INSERT INTO documents (id, owner_id, filename, mime, size, file_hash, "
                "storage_path, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (doc_id, owner_id, filename, mime, size, file_hash, storage_path, status, _now()),
            )
            self._db.commit()
        return doc_id

    def update_document_status(self, doc_id, status, page_count=None, summary=None) -> None:
        sets = ["status = ?"]
        vals: list = [status]
        if page_count is not None:
            sets.append("page_count = ?")
            vals.append(page_count)
        if summary is not None:
            sets.append("summary = ?")
            vals.append(summary)
        vals.append(doc_id)
        with self._lock:
            self._db.execute(f"UPDATE documents SET {', '.join(sets)} WHERE id = ?", vals)
            self._db.commit()

    def set_document_roles(self, doc_id, roles) -> None:
        with self._lock:
            self._db.execute("DELETE FROM document_roles WHERE document_id = ?", (doc_id,))
            self._db.executemany(
                "INSERT OR IGNORE INTO document_roles (document_id, role) VALUES (?, ?)",
                [(doc_id, r) for r in roles],
            )
            self._db.commit()

    def _roles_for(self, doc_id: str) -> list[str]:
        rows = self._db.execute(
            "SELECT role FROM document_roles WHERE document_id = ?", (doc_id,)
        ).fetchall()
        return [r["role"] for r in rows]

    def _row_to_doc(self, row: sqlite3.Row) -> DocumentRecord:
        chunk_count = self._db.execute(
            "SELECT COUNT(*) c FROM chunks WHERE document_id = ?", (row["id"],)
        ).fetchone()["c"]
        return DocumentRecord(
            id=row["id"],
            owner_id=row["owner_id"],
            filename=row["filename"],
            mime=row["mime"],
            size=row["size"],
            page_count=row["page_count"],
            status=row["status"],
            file_hash=row["file_hash"],
            storage_path=row["storage_path"],
            summary=row["summary"],
            created_at=row["created_at"],
            roles=self._roles_for(row["id"]),
            chunk_count=chunk_count,
        )

    def get_document(self, doc_id) -> DocumentRecord | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            return self._row_to_doc(row) if row else None

    def find_document_by_hash(self, owner_id, file_hash) -> DocumentRecord | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM documents WHERE owner_id = ? AND file_hash = ? ORDER BY created_at DESC LIMIT 1",
                (owner_id, file_hash),
            ).fetchone()
            return self._row_to_doc(row) if row else None

    def list_documents(self, owner_id) -> list[DocumentRecord]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM documents WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)
            ).fetchall()
            return [self._row_to_doc(r) for r in rows]

    def delete_document(self, doc_id) -> None:
        with self._lock:
            self._db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            self._db.execute("DELETE FROM document_roles WHERE document_id = ?", (doc_id,))
            self._db.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            self._db.execute("DELETE FROM chunks_fts WHERE document_id = ?", (doc_id,))
            self._db.commit()

    # ── Chunks ───────────────────────────────────────────────────────────────
    def add_chunks(self, doc_id, chunks) -> None:
        with self._lock:
            for c in chunks:
                cid = c.id or uuid.uuid4().hex
                self._db.execute(
                    "INSERT INTO chunks (id, document_id, page, ordinal, kind, content, "
                    "embedding, token_count) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        cid,
                        doc_id,
                        c.page,
                        c.ordinal,
                        c.kind,
                        c.content,
                        json.dumps(c.embedding) if c.embedding is not None else None,
                        c.token_count,
                    ),
                )
                self._db.execute(
                    "INSERT INTO chunks_fts (content, chunk_id, document_id) VALUES (?,?,?)",
                    (c.content, cid, doc_id),
                )
            self._db.commit()

    def count_chunks(self, doc_id) -> int:
        with self._lock:
            return self._db.execute(
                "SELECT COUNT(*) c FROM chunks WHERE document_id = ?", (doc_id,)
            ).fetchone()["c"]

    # ── Embedding cache ──────────────────────────────────────────────────────
    def get_cached_embedding(self, content_hash) -> list[float] | None:
        with self._lock:
            row = self._db.execute(
                "SELECT embedding FROM embedding_cache WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            return json.loads(row["embedding"]) if row else None

    def cache_embedding(self, content_hash, embedding) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO embedding_cache (content_hash, embedding) VALUES (?, ?)",
                (content_hash, json.dumps(embedding)),
            )
            self._db.commit()

    # ── Conversations & messages ─────────────────────────────────────────────
    def create_conversation(self, owner_id, title="New conversation") -> str:
        conv_id = uuid.uuid4().hex
        with self._lock:
            self._db.execute(
                "INSERT INTO conversations (id, owner_id, title, created_at) VALUES (?,?,?,?)",
                (conv_id, owner_id, title, _now()),
            )
            self._db.commit()
        return conv_id

    def get_conversation(self, conversation_id) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_conversations(self, owner_id) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM conversations WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def update_conversation(self, conversation_id, **fields) -> None:
        allowed = {"title", "summary", "working_set", "active_role"}
        sets, vals = [], []
        for key, value in fields.items():
            if key in allowed:
                sets.append(f"{key} = ?")
                vals.append(value)
        if not sets:
            return
        vals.append(conversation_id)
        with self._lock:
            self._db.execute(f"UPDATE conversations SET {', '.join(sets)} WHERE id = ?", vals)
            self._db.commit()

    def add_message(
        self, conversation_id, role, content, strategy=None, grounding=None, confidence=None, sources=None
    ) -> str:
        msg_id = uuid.uuid4().hex
        with self._lock:
            self._db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, strategy, grounding, "
                "confidence, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    msg_id,
                    conversation_id,
                    role,
                    content,
                    strategy,
                    json.dumps(grounding) if grounding is not None else None,
                    confidence,
                    _now(),
                ),
            )
            for rank, src in enumerate(sources or []):
                self._db.execute(
                    "INSERT INTO message_sources (message_id, chunk_id, document_id, page, snippet, rank) "
                    "VALUES (?,?,?,?,?,?)",
                    (
                        msg_id,
                        src.get("chunk_id", ""),
                        src.get("document_id", ""),
                        src.get("page", 0),
                        src.get("snippet", ""),
                        rank,
                    ),
                )
            self._db.commit()
        return msg_id

    def get_messages(self, conversation_id) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY rowid", (conversation_id,)
            ).fetchall()
            out = []
            for r in rows:
                sources = self._db.execute(
                    "SELECT chunk_id, document_id, page, snippet, rank FROM message_sources "
                    "WHERE message_id = ? ORDER BY rank",
                    (r["id"],),
                ).fetchall()
                out.append(
                    {
                        "id": r["id"],
                        "role": r["role"],
                        "content": r["content"],
                        "strategy": r["strategy"],
                        "grounding": json.loads(r["grounding"]) if r["grounding"] else None,
                        "confidence": r["confidence"],
                        "created_at": r["created_at"],
                        "sources": [dict(s) for s in sources],
                    }
                )
            return out

    # ── Audit log ────────────────────────────────────────────────────────────
    def add_audit(self, conversation_id, message_id, entries) -> None:
        with self._lock:
            for e in entries:
                self._db.execute(
                    "INSERT INTO audit_log (id, conversation_id, message_id, actor, action, target, "
                    "role_context, ts) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        uuid.uuid4().hex,
                        conversation_id,
                        message_id,
                        e.get("actor", ""),
                        e.get("action", ""),
                        e.get("target", ""),
                        e.get("role_context"),
                        _now(),
                    ),
                )
            self._db.commit()

    def get_audit(self, conversation_id) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT actor, action, target, role_context, ts FROM audit_log "
                "WHERE conversation_id = ? ORDER BY rowid",
                (conversation_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Query cache ──────────────────────────────────────────────────────────
    def get_cached_query(self, key) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT answer FROM query_cache WHERE key = ?", (key,)
            ).fetchone()
            return json.loads(row["answer"]) if row else None

    def set_cached_query(self, key, payload) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO query_cache (key, answer, created_at) VALUES (?,?,?)",
                (key, json.dumps(payload), _now()),
            )
            self._db.commit()

    # ── Subscriptions ────────────────────────────────────────────────────────
    def get_subscription(self, owner_id) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM subscriptions WHERE owner_id = ?", (owner_id,)
            ).fetchone()
            return dict(row) if row else None

    def upsert_subscription(self, owner_id, **fields) -> None:
        allowed = {
            "tier",
            "stripe_customer_id",
            "stripe_subscription_id",
            "status",
            "current_period_end",
        }
        data = {k: v for k, v in fields.items() if k in allowed}
        with self._lock:
            exists = self._db.execute(
                "SELECT 1 FROM subscriptions WHERE owner_id = ?", (owner_id,)
            ).fetchone()
            if exists and data:
                sets = ", ".join(f"{k} = ?" for k in data)
                self._db.execute(
                    f"UPDATE subscriptions SET {sets} WHERE owner_id = ?",
                    [*data.values(), owner_id],
                )
            elif not exists:
                cols = ["owner_id", *data.keys()]
                placeholders = ",".join("?" * len(cols))
                self._db.execute(
                    f"INSERT INTO subscriptions ({', '.join(cols)}) VALUES ({placeholders})",
                    [owner_id, *data.values()],
                )
            self._db.commit()

    # ── Visibility (governance-aware) ────────────────────────────────────────
    def _visible_doc_ids(
        self, owner_id: str, allowed_roles: list[str] | None, document_ids: list[str] | None
    ) -> list[str]:
        rows = self._db.execute(
            "SELECT id FROM documents WHERE owner_id = ? AND status = 'ready'", (owner_id,)
        ).fetchall()
        ids = [r["id"] for r in rows]
        if document_ids is not None:
            wanted = set(document_ids)
            ids = [i for i in ids if i in wanted]
        if allowed_roles is not None:
            allowed = set(allowed_roles)
            ids = [i for i in ids if allowed.intersection(self._roles_for(i))]
        return ids

    # ── Retrieval ────────────────────────────────────────────────────────────
    def vector_search(
        self, owner_id, query_embedding, k=8, allowed_roles=None, document_ids=None
    ) -> list[RetrievedChunk]:
        with self._lock:
            visible = self._visible_doc_ids(owner_id, allowed_roles, document_ids)
            if not visible:
                return []
            placeholders = ",".join("?" * len(visible))
            rows = self._db.execute(
                f"SELECT c.id, c.document_id, c.page, c.kind, c.content, c.embedding, d.filename "
                f"FROM chunks c JOIN documents d ON d.id = c.document_id "
                f"WHERE c.document_id IN ({placeholders}) AND c.embedding IS NOT NULL",
                visible,
            ).fetchall()
        if not rows:
            return []
        matrix = np.array([json.loads(r["embedding"]) for r in rows], dtype=np.float32)
        q = np.array(query_embedding, dtype=np.float32)
        matrix_n = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
        q_n = q / (np.linalg.norm(q) + 1e-9)
        scores = matrix_n @ q_n
        top = np.argsort(-scores)[:k]
        return [
            RetrievedChunk(
                chunk_id=rows[i]["id"],
                document_id=rows[i]["document_id"],
                filename=rows[i]["filename"],
                page=rows[i]["page"],
                kind=rows[i]["kind"],
                content=rows[i]["content"],
                score=float(scores[i]),
            )
            for i in top
        ]

    def keyword_search(
        self, owner_id, query, k=8, allowed_roles=None, document_ids=None
    ) -> list[RetrievedChunk]:
        terms = [t for t in "".join(ch if ch.isalnum() else " " for ch in query).split() if t]
        if not terms:
            return []
        match = " OR ".join(terms)
        with self._lock:
            visible = self._visible_doc_ids(owner_id, allowed_roles, document_ids)
            if not visible:
                return []
            placeholders = ",".join("?" * len(visible))
            rows = self._db.execute(
                f"SELECT f.chunk_id, f.document_id, c.page, c.kind, c.content, d.filename, "
                f"bm25(chunks_fts) AS score "
                f"FROM chunks_fts f JOIN chunks c ON c.id = f.chunk_id "
                f"JOIN documents d ON d.id = f.document_id "
                f"WHERE chunks_fts MATCH ? AND f.document_id IN ({placeholders}) "
                f"ORDER BY score LIMIT ?",
                [match, *visible, k],
            ).fetchall()
        # bm25 returns lower = better; flip sign so higher = better for fusion.
        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                filename=r["filename"],
                page=r["page"],
                kind=r["kind"],
                content=r["content"],
                score=-float(r["score"]),
            )
            for r in rows
        ]
