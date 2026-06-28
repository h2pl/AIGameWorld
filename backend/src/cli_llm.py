"""LLM 集成测试 CLI。用法: python -m src.cli_llm (需先配 .env 里的 DEEPSEEK_API_KEY)"""

import asyncio
import os

from src.config import load_config
from src.agents.llm_client import LLMClient
from src.agents.dm_agent import DMAgent
from src.engine.orchestrator import Orchestrator


async def test_llm_client() -> None:
    """测试 LLMClient 基础调用."""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ 未设置 DEEPSEEK_API_KEY，跳过 LLM 测试。请在 .env 里配置。")
        return

    config = load_config("config.yaml")
    client = LLMClient(config.llm)
    print(f"LLMClient initialized: {len(client._models)} models configured")

    # 简单调用测试
    from langchain_core.messages import HumanMessage, SystemMessage

    result = await client.call(
        "dm_create",
        [SystemMessage(content="Reply in one word."), HumanMessage(content="Hello")],
    )
    print(f"LLM call result: {result[:80] if result else 'None'}...")
    print("✅ LLMClient works!")


async def test_dm_agent() -> None:
    """测试 DMAgent 创造情境 + 叙事."""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ 未设置 DEEPSEEK_API_KEY，跳过 DMAgent 测试。")
        return

    config = load_config("config.yaml")
    client = LLMClient(config.llm)
    agent = DMAgent(client)

    # 测试创造情境
    print("\n--- create_situation ---")
    result = await agent.create_situation(plot_brief_prev="The party rests at camp.")
    print(f"  plot_brief: {result['plot_brief'][:100]}")
    print(f"  scene_direction: {result['scene_direction']}")

    # 测试叙事
    print("\n--- narrate ---")
    actions = [
        {"character_id": "alex", "type": "explore", "description": "Alex scouts ahead."},
        {"character_id": "maya", "type": "social", "description": "Maya talks to a traveler."},
    ]
    result2 = await agent.narrate(
        plot_brief="The party encounters a strange traveler on the road.",
        character_actions=actions,
    )
    print(f"  narrative: {result2['narrative'][:200]}")
    print("✅ DMAgent works!")


async def test_full_tick_with_llm() -> None:
    """全链路：Graph + LLM。"""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ 未设置 DEEPSEEK_API_KEY，跳过。")
        return

    config = load_config("config.yaml")
    client = LLMClient(config.llm)
    agent = DMAgent(client)

    orch = Orchestrator(dm_agent=agent)
    print("Orchestrator with DMAgent initialized. Running 1 tick...\n")

    result = await orch.run_tick()
    print(f"[Tick {result['tick']}]")
    print(f"  [DM] {result.get('narrative', '')[:200]}")
    for a in result.get("character_actions", [])[:3]:
        print(f"  [Act] {a.get('character_id','?')}({a.get('type','?')}): {a.get('description','')}")
    print("\n✅ Full tick with LLM works!")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="LLM 集成测试")
    parser.add_argument("--client", action="store_true", help="Test LLMClient only")
    parser.add_argument("--agent", action="store_true", help="Test DMAgent")
    parser.add_argument("--tick", action="store_true", help="Test full tick with LLM")
    parser.add_argument("--all", action="store_true", help="Test everything")

    args = parser.parse_args()
    run_all = args.all or not (args.client or args.agent or args.tick)

    if run_all or args.client:
        asyncio.run(test_llm_client())
    if run_all or args.agent:
        asyncio.run(test_dm_agent())
    if run_all or args.tick:
        asyncio.run(test_full_tick_with_llm())


if __name__ == "__main__":
    main()
