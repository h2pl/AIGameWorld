"""Memory Service——为各引擎提供按需记忆注入 / Memory injection service for engines.

统一封装短期/中期/长期记忆的检索，供 prompt 注入。
"""

from langchain_core.runnables.config import RunnableConfig

from ..utils.helpers import get_repo


async def retrieve_memories(
    pc_id: str,
    query: str,
    config: RunnableConfig = None,
    top_k: int = 5,
) -> list[str]:
    """按角色 + 查询语义检索相关记忆文本 / Retrieve relevant memory texts for a character.

    返回按重要性排序的记忆内容列表；无记忆或 repo 不可用时返回空列表。
    同时包含观察记忆与反思记忆，用于指导角色下一步行动。
    """
    memory_repo = get_repo(config, "memory")
    if not memory_repo:
        return []
    try:
        observations = await memory_repo.retrieve(pc_id, query, top_k=top_k)
        reflections = await memory_repo.retrieve_reflections(pc_id, query, top_k=3)
        seen: set[str] = set()
        contents: list[str] = []
        for m in observations + reflections:
            content = getattr(m, "content", None)
            if content and content not in seen:
                contents.append(content)
                seen.add(content)
        return contents
    except TypeError:
        return []
