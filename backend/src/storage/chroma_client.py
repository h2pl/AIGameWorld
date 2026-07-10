"""ChromaClient — 纯 ChromaDB 裸操作，零业务知识."""

import contextlib
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from src.utils.logging import get_logger

logger = get_logger(__name__)


def _bge_m3_ef() -> Any:
    """创建 BGE-M3 嵌入函数 / Create BGE-M3 embedding function.

    BGE-M3 是中文语义检索的最佳开源选择：
    - 支持多语言（中英日韩等 100+ 语言）
    - 支持多粒度（dense + sparse + colbert）
    - 在 MTEB/BEIR 中文排行榜名列前茅
    """
    try:
        from chromadb.utils import embedding_functions

        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-m3",
            # 正常情况下自动下载；离线环境需预先放置到 cache
        )
        logger.info("[chroma] BGE-M3 embedding function created")
        return ef
    except Exception as e:
        logger.warning("[chroma] BGE-M3 unavailable (%s), falling back to default", e)
        return None


class ChromaClient:
    """ChromaDB 连接 + 通用增删查 / ChromaDB connection + CRUD."""

    def __init__(self, persist_path: str | Path, embedding_function: Any | None = None):
        self._client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._ef = embedding_function
        if self._ef:
            logger.info("[chroma] using custom embedding function")
        else:
            logger.info("[chroma] using default embedding function")

    @classmethod
    def create_with_bge_m3(cls, persist_path: str | Path) -> "ChromaClient":
        """工厂方法：创建使用 BGE-M3 的 ChromaClient / Factory: create with BGE-M3."""
        ef = _bge_m3_ef()
        return cls(persist_path=persist_path, embedding_function=ef)

    # ── Collection ──
    def get_collection(self, name: str) -> chromadb.Collection:
        kwargs: dict[str, Any] = {}
        if self._ef:
            kwargs["embedding_function"] = self._ef
        return self._client.get_or_create_collection(name, **kwargs)

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
        # include distances in the query to support semantic scoring later
        res = col.query(
            query_texts=[query_text], 
            n_results=top_k, 
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        out = []
        # Handle cases where distances might be None or empty
        distances = res.get("distances", [[]])
        if not distances:
            distances = [[]]
            
        for i, (d, m) in enumerate(zip(res["documents"][0], res["metadatas"][0], strict=True)):
            dist = distances[0][i] if len(distances[0]) > i else 1.0
            out.append({"text": d, "meta": m, "distance": dist})
        return out
