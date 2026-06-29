"""LLM 集成测试 CLI。用法: python -m src.cli_llm --all"""

import asyncio
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import load_config
from src.engine.orchestrator import Orchestrator
from src.llm.llm_client import LLMClient

_PROMPTS = Environment(loader=FileSystemLoader(Path(__file__).parent / "prompts"))

_SEP = "=" * 60
_SUB = "-" * 40


async def test_llm_client() -> None:
    """测试 LLMClient 基础调用."""
    config = load_config("../config.yaml")
    client = LLMClient(config.llm)

    print(f"\n{_SEP}")
    print("  LLMClient 基础调用测试")
    print(
        f"  models: {len(client._models)} configured, provider: {config.llm.providers.primary.base_url}"
    )
    print(_SEP)

    msgs = [SystemMessage(content="Reply in one word."), HumanMessage(content="Hello")]
    print(f"  [INPUT]  messages: {[m.content[:30] for m in msgs]}")
    print(_SUB)

    result = await client.call("dm_create", msgs)
    print(f"  [OUTPUT] {result[:120] if result else 'None'}")
    print(_SUB)
    print("  LLMClient 基础调用 OK")


async def test_dm_engine() -> None:
    """测试 DM engine + LLM."""
    config = load_config("../config.yaml")
    client = LLMClient(config.llm)

    from src.engine.dm.dm import dm_create, dm_narrate
    from src.schemas.request import DMCreateRequest, DMNarrateRequest

    # ── dm_create ──
    print(f"\n{_SEP}")
    print("  DM Engine: dm_create (Phase 1)")
    print(_SEP)

    create_req = DMCreateRequest(tick=0, plot_brief="")
    prompt = _PROMPTS.get_template("dm/dm_create.jinja").render(
        story_arcs=[],
        active_hooks=[],
        recent_summary="",
        plot_brief_prev=create_req.plot_brief,
        pacing={},
    )
    print(f"  [INPUT]  tick={create_req.tick}, plot_brief_prev='{create_req.plot_brief}'")
    print(f"  [INPUT]  rendered prompt:\n{prompt}")
    print(_SUB)

    result = await dm_create(create_req, client)
    print(f"  [OUTPUT] plot_brief: {result.plot_brief}")
    print(f"  [OUTPUT] instructions ({len(result.instructions_out)}): {result.instructions_out}")
    print(f"  [OUTPUT] scene_direction: {json.dumps(result.scene_direction, ensure_ascii=False)}")
    print(_SUB)
    print("  dm_create OK")

    # ── dm_narrate ──
    print(f"\n{_SEP}")
    print("  DM Engine: dm_narrate (Phase 6)")
    print(_SEP)

    narrate_req = DMNarrateRequest(
        tick=0,
        plot_brief="The party encounters a strange traveler.",
        dm_instructions=[],
        scene_direction={},
        character_actions=[{"character_id": "alex", "type": "explore"}],
    )
    prompt_n = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
        plot_brief=narrate_req.plot_brief,
        character_actions=narrate_req.character_actions,
        events=[],
        combat_result=None,
        cast_changes=[],
    )
    print(f"  [INPUT]  tick={narrate_req.tick}")
    print(f"  [INPUT]  plot_brief: {narrate_req.plot_brief}")
    print(f"  [INPUT]  character_actions: {narrate_req.character_actions}")
    print(f"  [INPUT]  rendered prompt:\n{prompt_n}")
    print(_SUB)

    result2 = await dm_narrate(narrate_req, client)
    print(f"  [OUTPUT] narrative: {result2.narrative_out}")
    print(f"  [OUTPUT] branch_points: {result2.branch_points}")
    print(f"  [OUTPUT] hooks_resolved: {result2.hooks_resolved}")
    print(_SUB)
    print("  dm_narrate OK")


async def test_full_tick_with_llm() -> None:
    """全链路：Graph + LLM."""
    config = load_config("../config.yaml")
    client = LLMClient(config.llm)
    orch = Orchestrator(llm=client)

    print(f"\n{_SEP}")
    print("  Full Tick: Orchestrator + Graph + LLM")
    print(f"  provider: {config.llm.providers.primary.base_url}")
    print(_SEP)

    print(f"  [INPUT]  initial tick=0, llm={type(client).__name__}")
    print(_SUB)

    result = await orch.run_tick()
    print(f"  [OUTPUT] Tick {result['tick']}")
    print(f"  [OUTPUT] DM narrative: {result.get('narrative', '')}")
    for a in result.get("character_actions", [])[:5]:
        print(
            f"  [OUTPUT] Act: {a.get('character_id', '?')}({a.get('type', '?')}): {a.get('description', '')}"
        )
    errs = result.get("errors", [])
    if errs:
        print(f"  [OUTPUT] errors: {errs}")
    print(_SUB)
    print("  Full Tick OK")


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
