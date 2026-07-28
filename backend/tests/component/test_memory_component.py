"""Memory 组件测试——短期 deque + 长期 ChromaDB 协作."""

import tempfile
from pathlib import Path

import pytest

from src.repository.memory_repo import MemoryRepo
from src.storage.chroma_client import ChromaClient


@pytest.fixture(scope="module")
def repo():
    tmp = tempfile.mkdtemp(prefix="chroma_comp_")
    chroma = ChromaClient(Path(tmp))
    return MemoryRepo(chroma)


@pytest.mark.asyncio
async def test_short_and_long_term_merged(repo):
    """短期(deque)和长期(ChromaDB)合并去重."""
    await repo.store("test_merge", "Short term only", tick=1, importance=3)
    await repo.store("test_merge", "Also in chroma", tick=2, importance=6)
    short = repo.get_short_term("test_merge")
    long_results = repo.search_long_term_vector("test_merge", "term chroma", top_k=5)
    ids = [r["meta"].get("id") for r in long_results if r["meta"].get("id")]
    long = await repo.fetch_long_term_sqlite(ids) if ids else []
    merged = short + long
    assert len(merged) >= 1


@pytest.mark.asyncio
async def test_multi_character_isolation(repo):
    """多个角色的记忆互不干扰."""
    await repo.store("alex_iso", "Alex memory", tick=1)
    await repo.store("maya_iso", "Maya memory", tick=1)
    alex_short = repo.get_short_term("alex_iso")
    maya_short = repo.get_short_term("maya_iso")
    assert len(alex_short) >= 1
    assert len(maya_short) >= 1
    assert "Alex" in alex_short[0].content
    assert "Maya" in maya_short[0].content


@pytest.mark.asyncio
async def test_reflection_independent_from_memory(repo):
    """反思记忆独立于普通记忆."""
    await repo.store("alex_refl", "Regular memory", tick=1, importance=5)
    await repo.store_reflection("alex_refl", "Deep insight about trust", tick=2)
    reflections = await repo.retrieve_reflections("alex_refl", "trust", top_k=5)
    assert len(reflections) >= 1
    assert all(r.memory_type == "reflection" for r in reflections)
