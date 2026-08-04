"""ChromaClient — 纯 ChromaDB 裸操作，零业务知识."""

import contextlib
import os
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

    加载策略：优先从本地 HF 缓存加载（离线友好，避免联网超时）；
    若本地无缓存则回退到联网下载。
    """
    try:
        from chromadb.utils import embedding_functions

        model_name = _resolve_bge_m3_model_name()
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name,
        )
        logger.info("[chroma] BGE-M3 embedding function created (model=%s)", model_name)
        return ef
    except Exception as e:
        logger.warning("[chroma] BGE-M3 unavailable (%s), falling back to default", e)
        return None


def _resolve_bge_m3_model_name() -> str:
    """解析 BGE-M3 模型名 / Resolve BGE-M3 model name.

    优先返回本地 HF 缓存中 BAAI/bge-m3 的 snapshot 绝对路径，
    使离线环境下 sentence-transformers 无需联网解析 revision 即可加载。
    兼容新旧两种 HF 缓存目录结构：
      - 新版：hub/models--BAAI--bge-m3/snapshots/<rev>/
      - 旧版：hub/models/BAAI--bge-m3/snapshots/<rev>/
    若均不存在则返回标准模型名（触发联网下载）。
    """
    hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    candidates = [
        hf_home / "hub" / "models--BAAI--bge-m3" / "snapshots",
        hf_home / "hub" / "models" / "BAAI--bge-m3" / "snapshots",
    ]
    for base in candidates:
        if base.exists():
            snapshots = [p for p in base.iterdir() if p.is_dir()]
            if snapshots:
                # 取最新修改的 snapshot（通常即 main/master）
                latest = max(snapshots, key=lambda p: p.stat().st_mtime)
                return str(latest)
    return "BAAI/bge-m3"


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
        try:
            return self._client.get_or_create_collection(name, **kwargs)
        except ValueError as e:
            # 已存在的集合是用旧嵌入函数（默认 all-MiniLM，384 维）建的，
            # 现在用 BGE-M3（1024 维）打开会触发 embedding function 冲突。
            # 做一次性的维度迁移：删旧集合、用当前 ef 重建（空集合）。
            # 之后该集合的 ef 配置会被持久化，后续启动不再冲突。
            msg = str(e).lower()
            if "embedding function" in msg or "conflict" in msg:
                logger.warning(
                    "[chroma] collection %s embedding conflict, migrating to current ef (drops old vectors)",
                    name,
                )
                with contextlib.suppress(Exception):
                    self._client.delete_collection(name)
                return self._client.get_or_create_collection(name, **kwargs)
            raise

    def delete_collection(self, name: str) -> None:
        with contextlib.suppress(ValueError, Exception):
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
            include=["documents", "metadatas", "distances"],
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
