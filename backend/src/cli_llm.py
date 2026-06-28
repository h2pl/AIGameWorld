"""LLM 集成测试 CLI。用法: python -m src.cli_llm (Zen Proxy 无需 API key)"""

import asyncio

from src.config import load_config
from src.llm.llm_client import LLMClient
from src.engine.orchestrator import Orchestrator


async def test_llm_client() -> None:
    """测试 LLMClient 基础调用."""
    config = load_config("config.yaml")
    client = LLMClient(config.llm)
    print(f"LLMClient initialized: {len(client._models)} models configured")

    from langchain_core.messages import SystemMessage, HumanMessage

    result = await client.call(
        "dm_create",
        [SystemMessage(content="Reply in one word."), HumanMessage(content="Hello")],
    )
    print(f"LLM call result: {result[:80] if result else 'None'}...")
    print("LLMClient works!")


async def test_dm_engine() -> None:
    """测试 DM engine + LLM."""
    config = load_config("config.yaml")
    client = LLMClient(config.llm)

    from src.engine.dm.dm import dm_create, dm_narrate
    from src.schemas.request import DMCreateRequest, DMNarrateRequest

    print("\n--- dm_create ---")
    result = await dm_create(DMCreateRequest(tick=0, plot_brief=""), client)
    print(f"  plot_brief: {result.plot_brief[:100]}")
    print(f"  scene_direction: {result.scene_direction}")

    print("\n--- dm_narrate ---")
    result2 = await dm_narrate(DMNarrateRequest(
        tick=0, plot_brief="The party encounters a strange traveler.",
        dm_instructions=[], scene_direction={},
        character_actions=[{"character_id": "alex", "type": "explore"}],
    ), client)
    print(f"  narrative: {result2.narrative_out[:200]}")
    print("DM engine works!")


async def test_full_tick_with_llm() -> None:
    """全链路：Graph + LLM."""
    config = load_config("config.yaml")
    client = LLMClient(config.llm)

    orch = Orchestrator(llm=client)
    print("Orchestrator with LLM initialized. Running 1 tick...\n")

    result = await orch.run_tick()
    print(f"[Tick {result['tick']}]")
    print(f"  [DM] {result.get('narrative', '')[:200]}")
    for a in result.get("character_actions", [])[:3]:
        print(f"  [Act] {a.get('character_id','?')}({a.get('type','?')}): {a.get('description','')}")
    print("\nFull tick with LLM works!")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="LLM 集成测试")
    parser.add_argument("--client", action="store_true", help="Test LLMClient only")
    parser.add_argument("--engine", action="store_true", help="Test DM engine")
    parser.add_argument("--tick", action="store_true", help="Test full tick with LLM")
    parser.add_argument("--all", action="store_true", help="Test everything")

    args = parser.parse_args()
    run_all = args.all or not (args.client or args.engine or args.tick)

    if run_all or args.client:
        asyncio.run(test_llm_client())
    if run_all or args.engine:
        asyncio.run(test_dm_engine())
    if run_all or args.tick:
        asyncio.run(test_full_tick_with_llm())


if __name__ == "__main__":
    main()
