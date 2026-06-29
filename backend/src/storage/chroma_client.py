"""ChromaClient — 纯 ChromaDB 裸操作，零业务知识."""

import contextlib
from pathlib import Path

import chromadb
from chromadb.config import Settings


class ChromaClient:
    """ChromDB 连接 + 通用增删查."""

    def __init__(self, persist_path: str | Path):
        self._client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False),
        )

    # ── Collection ──
    def get_collection(self, name: str) -> chromadb.Collection:
        return self._client.get_or_create_collection(name)

    def delete_collection(self, name: str) -> None:
        with contextlib.suppress(ValueError):
            self._client.delete_collection(name)

    # ── 增删查 ──
    def add(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        col = self.get_collection(collection)
        col.add(ids=ids, documents=documents, metadatas=metadatas)

    def query(
        self, collection: str, query_text: str, top_k: int = 5, where: dict | None = None
    ) -> list[dict]:
        col = self.get_collection(collection)
        if col.count() == 0:
            return []
        res = col.query(query_texts=[query_text], n_results=top_k, where=where)
        return [
            {"text": d, "meta": m}
            for d, m in zip(res["documents"][0], res["metadatas"][0], strict=True)
        ]
