"""Storage interface + record types shared by every backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChunkRecord:
    """A single indexable unit of a document."""

    content: str
    page: int
    ordinal: int
    kind: str  # text | table | ocr
    token_count: int
    embedding: list[float] | None = None
    id: str | None = None
    document_id: str | None = None


@dataclass
class DocumentRecord:
    id: str
    owner_id: str
    filename: str
    mime: str
    size: int
    page_count: int
    status: str  # queued | parsing | embedding | ready | failed
    file_hash: str
    storage_path: str
    summary: str
    created_at: str
    roles: list[str] = field(default_factory=list)
    chunk_count: int = 0


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    page: int
    kind: str
    content: str
    score: float


class Store(ABC):
    """Abstract persistence + retrieval layer."""

    # ── Documents ────────────────────────────────────────────────────────────
    @abstractmethod
    def create_document(
        self,
        owner_id: str,
        filename: str,
        mime: str,
        size: int,
        file_hash: str,
        storage_path: str,
        status: str = "queued",
    ) -> str:
        ...

    @abstractmethod
    def update_document_status(
        self,
        doc_id: str,
        status: str,
        page_count: int | None = None,
        summary: str | None = None,
    ) -> None:
        ...

    @abstractmethod
    def set_document_roles(self, doc_id: str, roles: list[str]) -> None:
        ...

    @abstractmethod
    def get_document(self, doc_id: str) -> DocumentRecord | None:
        ...

    @abstractmethod
    def find_document_by_hash(self, owner_id: str, file_hash: str) -> DocumentRecord | None:
        ...

    @abstractmethod
    def list_documents(self, owner_id: str) -> list[DocumentRecord]:
        ...

    @abstractmethod
    def delete_document(self, doc_id: str) -> None:
        ...

    # ── Chunks ───────────────────────────────────────────────────────────────
    @abstractmethod
    def add_chunks(self, doc_id: str, chunks: list[ChunkRecord]) -> None:
        ...

    @abstractmethod
    def count_chunks(self, doc_id: str) -> int:
        ...

    # ── Embedding cache ──────────────────────────────────────────────────────
    @abstractmethod
    def get_cached_embedding(self, content_hash: str) -> list[float] | None:
        ...

    @abstractmethod
    def cache_embedding(self, content_hash: str, embedding: list[float]) -> None:
        ...

    # ── Conversations & messages (dialogue memory) ───────────────────────────
    @abstractmethod
    def create_conversation(self, owner_id: str, title: str = "New conversation") -> str:
        ...

    @abstractmethod
    def get_conversation(self, conversation_id: str) -> dict | None:
        ...

    @abstractmethod
    def list_conversations(self, owner_id: str) -> list[dict]:
        ...

    @abstractmethod
    def update_conversation(self, conversation_id: str, **fields) -> None:
        ...

    @abstractmethod
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        strategy: str | None = None,
        grounding: dict | None = None,
        confidence: float | None = None,
        sources: list[dict] | None = None,
    ) -> str:
        ...

    @abstractmethod
    def get_messages(self, conversation_id: str) -> list[dict]:
        ...

    # ── Audit log ────────────────────────────────────────────────────────────
    @abstractmethod
    def add_audit(self, conversation_id: str, message_id: str | None, entries: list[dict]) -> None:
        ...

    @abstractmethod
    def get_audit(self, conversation_id: str) -> list[dict]:
        ...

    # ── Query cache ──────────────────────────────────────────────────────────
    @abstractmethod
    def get_cached_query(self, key: str) -> dict | None:
        ...

    @abstractmethod
    def set_cached_query(self, key: str, payload: dict) -> None:
        ...

    # ── Subscriptions (used from M8) ─────────────────────────────────────────
    @abstractmethod
    def get_subscription(self, owner_id: str) -> dict | None:
        ...

    @abstractmethod
    def upsert_subscription(self, owner_id: str, **fields) -> None:
        ...

    # ── Retrieval (used from M2) ─────────────────────────────────────────────
    @abstractmethod
    def vector_search(
        self,
        owner_id: str,
        query_embedding: list[float],
        k: int = 8,
        allowed_roles: list[str] | None = None,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        ...

    @abstractmethod
    def keyword_search(
        self,
        owner_id: str,
        query: str,
        k: int = 8,
        allowed_roles: list[str] | None = None,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        ...
