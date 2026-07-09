"""World Pack 知识库仓储 / World Pack Knowledge Repository.

管理世界观的向量检索 RAG：
- 加载时：将 World Pack YAML 数据分块 + 嵌入写入 ChromaDB
- 查询时：根据自然语言查询检索相关知识片段

集合命名：worldpack_{type}（如 worldpack_lore, worldpack_characters 等）
"""

from pathlib import Path
from typing import Any

import yaml

from ..storage.chroma_client import ChromaClient
from ..utils.logging import get_logger

logger = get_logger(__name__)

# 知识类型 → ChromaDB 集合名 / Knowledge type → collection name
_COLLECTION_TYPES = {
    "lore": "worldpack_lore",
    "characters": "worldpack_characters",
    "scenes": "worldpack_scenes",
    "items": "worldpack_items",
    "quests": "worldpack_quests",
}

# 最大 chunk 字符数 / Max chunk size in characters
_CHUNK_SIZE = 500
# chunk 重叠字符数 / Chunk overlap in characters
_CHUNK_OVERLAP = 50


def _chunk_text(
    text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP
) -> list[str]:
    """将长文本分块 / Split long text into chunks.

    简单的滑动窗口分块策略，适用于世界观文本。
    对于结构化数据（角色/物品），每个条目作为一个 chunk。
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


class KnowledgeRepo:
    """World Pack 知识库——分块嵌入 + 语义检索 / Knowledge base: chunk + embed + retrieve."""

    def __init__(self, chroma: ChromaClient):
        self._chroma = chroma
        self._indexed_packs: set[str] = set()  # 已索引的包名 / Indexed pack names

    async def index_pack(self, pack_path: Path, pack_name: str = "") -> int:
        """索引一个 World Pack 到 ChromaDB / Index a World Pack into ChromaDB.

        读取 YAML 文件，分块后写入对应集合。
        返回索引的 chunk 总数。
        """
        if not pack_path.is_dir():
            logger.warning("[knowledge] pack path not found: %s", pack_path)
            return 0

        pack_name = pack_name or pack_path.name
        if pack_name in self._indexed_packs:
            logger.info("[knowledge] pack %s already indexed, skipping", pack_name)
            return 0

        total_chunks = 0

        # ── lore：扫描 lore/ 子目录下所有 yaml / Scan lore/ subdirectory ──
        total_chunks += self._index_subdir(pack_path / "lore", _COLLECTION_TYPES["lore"], pack_name)

        # ── characters：扫描 actors/ + player_characters/ / Scan actors + player_characters ──
        total_chunks += self._index_subdir(
            pack_path / "actors",
            _COLLECTION_TYPES["characters"],
            pack_name,
        )
        total_chunks += self._index_subdir(
            pack_path / "player_characters",
            _COLLECTION_TYPES["characters"],
            pack_name,
        )

        # ── scenes：扫描 scenes/ 子目录 / Scan scenes/ subdirectory ──
        total_chunks += self._index_subdir(
            pack_path / "scenes", _COLLECTION_TYPES["scenes"], pack_name
        )

        # ── items：扫描 items/ 子目录 / Scan items/ subdirectory ──
        total_chunks += self._index_subdir(
            pack_path / "items", _COLLECTION_TYPES["items"], pack_name
        )

        # ── quests：扫描 story_setup.yaml / Scan story_setup.yaml ──
        story_setup = pack_path / "story_setup.yaml"
        if story_setup.exists():
            total_chunks += self._index_yaml(story_setup, _COLLECTION_TYPES["quests"], pack_name)

        self._indexed_packs.add(pack_name)
        logger.info("[knowledge] indexed pack=%s chunks=%d", pack_name, total_chunks)
        return total_chunks

    def _index_subdir(self, subdir: Path, collection_name: str, pack_name: str) -> int:
        """索引子目录下所有 YAML 文件 / Index all YAML files in a subdirectory."""
        if not subdir.is_dir():
            return 0
        total = 0
        for yaml_path in sorted(subdir.glob("*.yaml")):
            total += self._index_yaml(yaml_path, collection_name, pack_name)
        return total

    def _index_yaml(self, yaml_path: Path, collection_name: str, pack_name: str) -> int:
        """索引单个 YAML 文件 / Index a single YAML file."""
        try:
            with yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.warning("[knowledge] failed to load %s: %s", yaml_path, e)
            return 0

        if not data:
            return 0

        ids = []
        documents = []
        metadatas = []

        if isinstance(data, list):
            # 列表格式：每个条目作为独立 chunk / List format: each entry as a chunk
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    text = self._dict_to_text(item)
                    if text:
                        chunks = _chunk_text(text)
                        for j, chunk in enumerate(chunks):
                            chunk_id = f"{pack_name}_{collection_name}_{i}_{j}"
                            ids.append(chunk_id)
                            documents.append(chunk)
                            metadatas.append(
                                {
                                    "pack": pack_name,
                                    "type": collection_name,
                                    "source": yaml_path.name,
                                    "index": i,
                                    "chunk": j,
                                }
                            )
        elif isinstance(data, dict):
            # 字典格式：按顶层 key 分块 / Dict format: chunk by top-level key
            for key, value in data.items():
                if isinstance(value, str) and value:
                    chunks = _chunk_text(value)
                    for j, chunk in enumerate(chunks):
                        chunk_id = f"{pack_name}_{collection_name}_{key}_{j}"
                        ids.append(chunk_id)
                        documents.append(chunk)
                        metadatas.append(
                            {
                                "pack": pack_name,
                                "type": collection_name,
                                "source": yaml_path.name,
                                "key": key,
                                "chunk": j,
                            }
                        )
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            text = self._dict_to_text(item)
                            if text:
                                chunk_id = f"{pack_name}_{collection_name}_{key}_{i}"
                                ids.append(chunk_id)
                                documents.append(text)
                                metadatas.append(
                                    {
                                        "pack": pack_name,
                                        "type": collection_name,
                                        "source": yaml_path.name,
                                        "key": key,
                                        "index": i,
                                    }
                                )

        if ids:
            # 分批写入（ChromaDB 单次 add 上限）/ Batch add (ChromaDB add limit)
            batch_size = 100
            for start in range(0, len(ids), batch_size):
                self._chroma.add(
                    collection=collection_name,
                    ids=ids[start : start + batch_size],
                    documents=documents[start : start + batch_size],
                    metadatas=metadatas[start : start + batch_size],
                )

        return len(ids)

    @staticmethod
    def _dict_to_text(item: dict) -> str:
        """将字典条目转为可检索文本 / Convert dict entry to searchable text."""
        # 优先拼接关键字段 / Prioritize key fields
        priority_keys = [
            "name",
            "title",
            "id",
            "description",
            "content",
            "text",
            "backstory",
            "personality",
            "role",
            "race",
            "type",
        ]
        text_parts = []
        seen = set()

        for key in priority_keys:
            if key in item and key not in seen:
                val = item[key]
                if isinstance(val, str) and val:
                    text_parts.append(f"{key}: {val}")
                    seen.add(key)
                elif isinstance(val, list):
                    text_parts.append(f"{key}: {', '.join(str(v) for v in val)}")
                    seen.add(key)

        # 补充其他字段 / Append remaining fields
        for key, val in item.items():
            if key in seen:
                continue
            if isinstance(val, str) and val or isinstance(val, (int, float)):
                text_parts.append(f"{key}: {val}")
            elif isinstance(val, list) and val and isinstance(val[0], (str, int, float)):
                text_parts.append(f"{key}: {', '.join(str(v) for v in val)}")

        return "\n".join(text_parts)

    def retrieve(
        self,
        query: str,
        knowledge_types: list[str] | None = None,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """检索相关知识 / Retrieve relevant knowledge.

        Args:
            query: 自然语言查询 / Natural language query
            knowledge_types: 知识类型过滤（如 ["lore", "characters"]）/ Knowledge type filter
            top_k: 每种类型返回的最大条数 / Max results per type
        """
        types = knowledge_types or list(_COLLECTION_TYPES.keys())
        all_results: list[dict[str, Any]] = []

        for type_name in types:
            collection_name = _COLLECTION_TYPES.get(type_name)
            if not collection_name:
                continue
            results = self._chroma.query(
                collection=collection_name,
                query_text=query,
                top_k=top_k,
            )
            all_results.extend(
                {"text": r["text"], "type": type_name, "meta": r.get("meta", {})} for r in results
            )

        # 按 relevance 排序（ChromaDB 已按距离排序，保持原始顺序即可）
        return all_results[: top_k * len(types)]

    def retrieve_for_purpose(
        self,
        purpose: str,
        query: str,
        top_k: int = 3,
    ) -> str:
        """根据 LLM purpose 检索相关知识并格式化 / Retrieve and format knowledge for LLM purpose.

        返回格式化的知识文本，可直接注入 prompt 模板。
        """
        # 根据 purpose 决定检索哪些类型的知识 / Determine knowledge types by purpose
        purpose_type_map = {
            "dm_create": ["lore", "scenes", "characters", "quests"],
            "dm_narrate": ["lore", "scenes", "characters"],
            "pc_decision": ["scenes", "characters", "items"],
            "talk": ["characters", "lore"],
            "interact": ["items", "scenes", "characters"],
            "explore": ["scenes", "lore", "items"],
            "combat": ["characters", "items"],
            "reflection": ["lore", "characters"],
        }
        types = purpose_type_map.get(purpose, ["lore"])
        results = self.retrieve(query=query, knowledge_types=types, top_k=top_k)

        if not results:
            return ""

        # 格式化为可读文本 / Format as readable text
        lines = []
        for r in results:
            type_label = {
                "lore": "世界观",
                "characters": "角色",
                "scenes": "场景",
                "items": "物品",
                "quests": "任务",
            }.get(r["type"], r["type"])
            lines.append(f"【{type_label}】{r['text']}")

        return "\n".join(lines)

    async def clear(self, pack_name: str = "") -> None:
        """清空知识库 / Clear knowledge base."""
        for collection_name in _COLLECTION_TYPES.values():
            self._chroma.delete_collection(collection_name)
        self._indexed_packs.discard(pack_name)
        logger.info("[knowledge] cleared pack=%s", pack_name or "all")
