"""Studio 知识库 MCP client / MCP client for AIGameWorld Studio knowledge base.

主项目 backend 作为 MCP client，以 **stdio** 方式拉起 Studio 的 ``aw-studio mcp``
进程（FastMCP server），通过其暴露的 ``list_topics()`` / ``search()`` 工具检索
Studio 的 Qdrant 知识库。

设计要点：
- 与现有 ``KnowledgeRepo``（ChromaDB，World Pack YAML）解耦——Studio 用自己的
  Qdrant 向量库，主项目不直连，只通过 MCP 协议调用工具。
- 懒加载 + 模块级单例：首次检索时拉起子进程并缓存工具列表；失败则标记
  ``_available=False``，所有调用优雅降级返回空，不阻断主链路。
- 暴露 ``MCPKnowledgeClient``，方法与 ``KnowledgeRepo`` 对齐（retrieve / retrieve_for_purpose），
  方便 dm_engine 在启动时按 purpose 选择性切换到本 client。

依赖：langchain-mcp-adapters + mcp（已在 pyproject runtime 依赖中）。
"""

from __future__ import annotations

import asyncio
from typing import Any

from ..utils.logging import get_logger

logger = get_logger(__name__)


class MCPKnowledgeClient:
    """Studio 知识库 MCP client 单例封装 / MCP client wrapper for Studio KB."""

    def __init__(
        self,
        command: str = "aw-studio",
        args: list[str] | None = None,
        top_k: int = 5,
        timeout: int = 30,
        cwd: str | None = None,
    ):
        self._command = command
        self._args = args or ["mcp"]
        self._top_k = top_k
        self._timeout = timeout
        self._cwd = cwd  # 子进程工作目录（Studio 项目根，确保能 import src.mcp_server）

        # 运行时状态 / runtime state
        self._session: Any = None  # MCP ClientSession
        self._tools: list[Any] = []  # 缓存的工具列表
        self._tool_map: dict[str, Any] = {}  # name → tool
        self._available: bool | None = None  # None=未探测；True/False=结果
        self._default_topic: str | None = None  # list_topics 的第一个 topic
        self._lock = asyncio.Lock()
        self._started = False

    # ── 生命周期 / lifecycle ──
    async def _ensure_started(self) -> bool:
        """懒加载：拉起子进程 + 初始化 session + 缓存工具。

        返回是否可用（网络/进程失败则 False，但只探测一次）。
        """
        async with self._lock:
            if self._started:
                return self._available is True
            self._started = True
            try:
                from langchain_mcp_adapters.client import MultiServerMCPClient

                # stdio 传输：直接让 adapters 管理子进程生命周期
                conn: dict[str, Any] = {
                    "command": self._command,
                    "args": list(self._args),
                    "transport": "stdio",
                }
                if self._cwd:
                    conn["cwd"] = self._cwd
                client = MultiServerMCPClient({"studio_kb": conn})
                # 这会拉起子进程并连接；返回可用工具列表
                self._tools = await asyncio.wait_for(client.get_tools(), timeout=self._timeout)
                self._tool_map = {t.name: t for t in self._tools}
                if "search" not in self._tool_map or "list_topics" not in self._tool_map:
                    logger.warning(
                        "[mcp] Studio MCP 工具缺失（仅 %s），client 不可用",
                        list(self._tool_map.keys()),
                    )
                    self._available = False
                    return False
                self._available = True
                logger.info("[mcp] Studio MCP 已连接，工具: %s", list(self._tool_map.keys()))
                return True
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "[mcp] Studio MCP 连接失败（%s），降级回主项目 KnowledgeRepo: %s",
                    type(e).__name__,
                    e,
                )
                self._available = False
                return False

    async def _call_tool(self, name: str, **kwargs: Any) -> Any:
        """调用一个 MCP 工具（内部会确保已连接）。"""
        if not await self._ensure_started():
            return None
        tool = self._tool_map.get(name)
        if tool is None:
            return None
        try:
            result = await asyncio.wait_for(tool.ainvoke(kwargs), timeout=self._timeout)
            return result
        except Exception as e:  # noqa: BLE001
            logger.warning("[mcp] tool %s 调用失败: %s", name, e)
            return None

    # ── 对外 API（对齐 KnowledgeRepo）─────────────────────────────
    async def is_available(self) -> bool:
        """探测 Studio MCP 是否可用 / Probe availability."""
        return await self._ensure_started()

    async def list_topics(self) -> list[dict[str, Any]]:
        """列出 Studio 知识库全部主题 / List all topics."""
        res = await self._call_tool("list_topics")
        if res is None:
            return []
        if isinstance(res, dict):
            return res.get("topics", []) or []
        return []

    async def _resolve_topic(self) -> str | None:
        """确定默认检索 topic：配置指定 > list_topics 第一个。"""
        if self._default_topic:
            return self._default_topic
        topics = await self.list_topics()
        if topics:
            self._default_topic = topics[0].get("topic")
        return self._default_topic

    async def search(
        self,
        query: str,
        topic: str | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """在指定（或默认）topic 下检索知识 / Search knowledge in a topic."""
        topic = topic or await self._resolve_topic()
        if not topic:
            return []
        k = top_k or self._top_k
        res = await self._call_tool("search", topic_slug=topic, query=query, top_k=k)
        if res is None:
            return []
        if isinstance(res, dict):
            return res.get("hits", []) or []
        return []

    async def retrieve_for_purpose(
        self,
        purpose: str,
        query: str,
        top_k: int | None = None,
    ) -> str:
        """对齐 KnowledgeRepo.retrieve_for_purpose：检索并格式化为可注入文本。

        注意：Studio 是单一跨类型知识库（按 topic 组织），不区分 worldpack 的
        lore/characters/scenes 类型，因此这里把所有命中统一格式化为【知识】。
        """
        hits = await self.search(query=query, top_k=top_k)
        if not hits:
            return ""
        lines = []
        for h in hits:
            text = (h.get("text") or "").strip()
            if text:
                lines.append(f"【知识】{text}")
        return "\n".join(lines)

    async def close(self) -> None:
        """关闭资源（当前 tools 由 adapters 管理子进程，这里只复位状态）。"""
        self._session = None
        self._tools = []
        self._tool_map = {}
        self._available = None
        self._started = False


# 模块级单例 / module-level singleton（server.py 启动时构造并放入 repos）
class _MCPClientHolder:
    """持有单例，避免 global 语句（PLW0603）。"""

    client: MCPKnowledgeClient | None = None


_holder = _MCPClientHolder()


def get_mcp_client() -> MCPKnowledgeClient | None:
    """获取单例（未初始化返回 None）。"""
    return _holder.client


def init_mcp_client(
    command: str = "aw-studio",
    args: list[str] | None = None,
    top_k: int = 5,
    timeout: int = 30,
    cwd: str | None = None,
) -> MCPKnowledgeClient:
    """构造并缓存单例 / Construct and cache the singleton."""
    _holder.client = MCPKnowledgeClient(
        command=command, args=args, top_k=top_k, timeout=timeout, cwd=cwd
    )
    return _holder.client
