"""CLI 入口 / CLI entry point.

用法:
  python -m src.cli run --ticks 5              # 纯 mock，不写 DB
  python -m src.cli run --ticks 3 --db         # 全链路：DB 读写
  python -m src.cli run --ticks 3 --llm         # 真实 LLM，不写 DB
  python -m src.cli run --ticks 3 --db --llm   # 真实 LLM + DB 读写 + 种子数据
  python -m src.cli test all                    # LLM 诊断：测试所有组件
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from src.domain import (
    Actor,
    Attributes,
    CharacterArc,
    CombatStats,
    Location,
    PlayerCharacter,
    StoryArc,
    StoryHook,
)
from src.graph.orchestrator import Orchestrator
from src.repository.character_repo import CharacterRepo
from src.repository.memory_repo import MemoryRepo
from src.repository.story_repo import StoryRepo
from src.storage.chroma_client import ChromaClient
from src.storage.sqlite_client import SQLiteClient
from src.utils.logging import setup_logging

# ═══════════════════════════════════════════════════════════════
# 种子数据 / Seed data
# ═══════════════════════════════════════════════════════════════


def _seed_pcs() -> list[PlayerCharacter]:
    return [
        PlayerCharacter(
            id="alex",
            name="Alex",
            role="fighter",
            race="human",
            location=Location(scene_id="tavern"),
            attributes=Attributes(
                strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=12
            ),
            combat=CombatStats(hp=28, max_hp=28, ac=16, initiative=2, attack_bonus=5),
            character_arc=CharacterArc(stage="growth", description="Prove his worth as a warrior"),
        ),
        PlayerCharacter(
            id="maya",
            name="Maya",
            role="rogue",
            race="elf",
            location=Location(scene_id="tavern"),
            attributes=Attributes(
                strength=10, dexterity=18, constitution=12, intelligence=14, wisdom=12, charisma=14
            ),
            combat=CombatStats(hp=20, max_hp=20, ac=14, initiative=4, attack_bonus=6),
            character_arc=CharacterArc(stage="crisis", description="Struggling with trust issues"),
        ),
    ]


def _seed_actors() -> list[Actor]:
    return [
        Actor(
            id="innkeeper",
            name="Greta",
            role="innkeeper",
            race="dwarf",
            location=Location(scene_id="tavern"),
            attributes=Attributes(
                strength=12, dexterity=8, constitution=14, intelligence=10, wisdom=14, charisma=16
            ),
            personality="Warm but sharp-eyed. Knows everyone's secrets.",
            functions=["dialogue", "merchant"],
        ),
        Actor(
            id="guard",
            name="Sergeant Cole",
            role="town_guard",
            race="human",
            location=Location(scene_id="town_square"),
            attributes=Attributes(
                strength=14, dexterity=10, constitution=14, intelligence=10, wisdom=12, charisma=10
            ),
            combat=CombatStats(hp=22, max_hp=22, ac=15, initiative=1, attack_bonus=4),
            personality="Stern but fair. Served the town for 20 years.",
            functions=["guard", "dialogue"],
        ),
    ]


def _seed_story() -> tuple[list[StoryArc], list[StoryHook]]:
    """初始剧情线与伏笔种子 / Initial story arcs & hooks seed."""
    arcs = [
        StoryArc(
            id="main_01",
            type="main",
            title="酒馆的密信",
            stage="铺陈",
            main_cast=["alex", "maya"],
            supporting_actors=["innkeeper"],
        ),
        StoryArc(
            id="side_01",
            type="side",
            title="失踪的商队",
            stage="铺陈",
            main_cast=["alex"],
            supporting_actors=["guard"],
        ),
    ]
    hooks = [
        StoryHook(
            id="hook_01",
            planted_tick=0,
            description="旅店老板娘 Greta 似乎知道一些不为人知的秘密",
            intended_payoff="Greta 在关键时刻揭露真相",
        ),
        StoryHook(
            id="hook_02",
            planted_tick=0,
            description="镇广场巡逻队长 Cole 最近增派了人手，似乎在警戒什么",
            intended_payoff="发现商队失踪的真凶",
        ),
    ]
    return arcs, hooks


# ═══════════════════════════════════════════════════════════════
# 输出 / Output
# ═══════════════════════════════════════════════════════════════


def _print_tick(
    tick: int,
    narrative: str,
    actions: list,
    events: list,
    errors: list,
    db_info: str = "",
) -> None:
    print(f"{'=' * 60}")
    header = f"[Tick {tick}]" + (f"  {db_info}" if db_info else "")
    print(header)
    if narrative:
        print(f"  [DM] {narrative}")
    for a in actions:
        cid = a.get("character_id", "?")
        atype = a.get("action_type", a.get("type", "?"))
        desc = a.get("reasoning", a.get("description", ""))
        print(f"  [Act] {cid}({atype}): {desc}")
    for ev in events[:3]:
        print(f"  [Evt] {ev.get('type', '?')}: {ev.get('description', '')[:80]}")
    if errors:
        print(f"  [Err] {[e[:60] for e in errors]}")


# ═══════════════════════════════════════════════════════════════
# run 命令 / run command
# ═══════════════════════════════════════════════════════════════


async def run(args: argparse.Namespace) -> None:
    """统一入口：mock / LLM / DB 组合 / Unified entry: mock/LLM/DB combo."""
    n = args.ticks
    use_db = args.db
    use_llm = args.llm

    # 模式标签 / mode label
    mode_parts = []
    if use_llm:
        mode_parts.append("LLM")
    else:
        mode_parts.append("Mock")
    if use_db:
        mode_parts.append("+DB")
    else:
        mode_parts.append("(no DB)")

    print(f"Phase 1 -- {' '.join(mode_parts)}")
    print(f"Running {n} tick(s)...\n")

    db = None
    repos = None
    llm = None

    # -- DB 模式：初始化 + 种子 / DB mode: init + seed
    if use_db:
        db_path = args.db_path or "data/world_db.db"
        db = SQLiteClient(db_path)
        await db.connect()
        await db.init_schema()
        print("  [DB] initialized (15 tables)")

        repo = CharacterRepo(db)
        pcs = _seed_pcs()
        for pc in pcs:
            await repo.save_pc(pc)
        print(f"  [DB] Seeded {len(pcs)} PCs: {[p.name for p in pcs]}")

        actors = _seed_actors()
        for a in actors:
            await repo.save_actor(a)
        print(f"  [DB] Seeded {len(actors)} Actors: {[a.name for a in actors]}")

        story_repo = StoryRepo(db)
        arcs, hooks = _seed_story()
        for arc in arcs:
            await story_repo.save_arc(arc)
        for hook in hooks:
            await story_repo.save_hook(hook)
        await db.commit()
        print(f"  [DB] Seeded {len(arcs)} story arcs + {len(hooks)} hooks")

        repos = {"story": story_repo, "char": repo}

    # -- LLM 模式：创建客户端 / LLM mode: create client
    if use_llm:
        from src.config import load_config
        from src.llm.llm_client import LLMClient

        config = load_config("../config.yaml")
        llm = LLMClient(config.llm)
        provider_url = config.llm.providers.primary.base_url or "(default)"
        print(f"  [LLM] provider: {provider_url}")

        # LLM + DB 模式加 MemoryRepo / LLM+DB mode: add MemoryRepo
        chroma = ChromaClient(persist_path="data/chroma")
        if repos:
            repos["memory"] = MemoryRepo(chroma=chroma)
        else:
            repos = {"memory": MemoryRepo(chroma=chroma)}

    # -- Tick 循环 / Tick loop
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    orch = Orchestrator(llm=llm, repos=repos)

    for _ in range(n):
        result = await orch.run_tick()
        tick = result["tick"]
        narrative = result.get("narrative", "")
        events = result.get("events", [])
        actions = result.get("character_actions", [])
        errors = result.get("errors", [])

        # DB 写入 / DB write
        if db and narrative:
            await db.execute(
                "INSERT INTO narratives (tick, content) VALUES (?, ?)",
                (tick, narrative),
            )
            for j, ev in enumerate(events):
                await db.execute(
                    "INSERT INTO events (id, tick, seq, type, source, data_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (f"evt_{run_id}_{tick}_{j}", tick, j, ev.get("type", "?"), "dm", "{}"),
                )
            await db.execute(
                "INSERT OR REPLACE INTO world_meta (key, value) VALUES (?, ?)",
                ("current_tick", str(tick)),
            )
            await db.commit()

        db_label = f"[DB] ticks {tick}" if use_db else ""
        _print_tick(tick, narrative, actions, events, errors, db_info=db_label)

    # 收尾 / cleanup
    print(f"{'=' * 60}")
    if db:
        tick_row = await db.fetch_one("SELECT value FROM world_meta WHERE key = 'current_tick'")
        narrative_count = len(await db.fetch_all("SELECT id FROM narratives"))
        print(
            f"Done. DB: tick={tick_row['value'] if tick_row else '?'}, narratives={narrative_count}"
        )
        await db.close()
    else:
        print(f"Done. {n} tick(s) completed.")


# ═══════════════════════════════════════════════════════════════
# test 命令（诊断用 / diagnostic commands）
# ═══════════════════════════════════════════════════════════════

_SEP = "=" * 60
_SUB = "-" * 40


async def _test_client() -> None:
    """测试 LLMClient 基础调用 / Test LLMClient basic call."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.config import load_config
    from src.llm.llm_client import LLMClient

    config = load_config("../config.yaml")
    client = LLMClient(config.llm)

    print(f"\n{_SEP}")
    print("  LLMClient 基础调用测试 / Basic Call Test")
    print(f"  provider: {config.llm.providers.primary.base_url or '(default)'}")
    print(_SEP)

    msgs = [SystemMessage(content="Reply in one word."), HumanMessage(content="Hello")]
    print(f"  [INPUT]  messages: {[m.content[:30] for m in msgs]}")
    print(_SUB)

    result = await client.call("dm_create", msgs)
    print(f"  [OUTPUT] {result[:120] if result else 'None'}")
    print(_SUB)
    print("  LLMClient OK")


async def _test_engine() -> None:
    """测试 DM engine + LLM / Test DM engine with LLM."""
    from jinja2 import Environment, FileSystemLoader
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.config import load_config
    from src.llm.llm_client import LLMClient
    from src.schemas.request import DMCreateRequest, DMNarrateRequest

    config = load_config("../config.yaml")
    client = LLMClient(config.llm)
    prompts = Environment(loader=FileSystemLoader(Path(__file__).parent / "prompts"))

    # ── dm_create ──
    print(f"\n{_SEP}")
    print("  DM Engine: dm_create (Phase 1)")
    print(_SEP)

    create_req = DMCreateRequest(tick=0, plot_brief="")
    system_prompt = prompts.get_template("_dm_system.jinja").render()
    prompt = prompts.get_template("dm/dm_create.jinja").render(
        story_arcs=[],
        active_hooks=[],
        recent_summary="",
        plot_brief_prev=create_req.plot_brief,
        pacing={},
    )
    print(f"  [INPUT]  tick={create_req.tick}")
    print(f"  [INPUT]  system:\n{system_prompt[:200]}...")
    print(f"  [INPUT]  prompt:\n{prompt[:300]}...")
    print(_SUB)

    # Engine 现在收 (req, config)，诊断测试直接调 call_structured
    msgs = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt),
    ]
    result_raw = await client.call_structured("dm_create", None, msgs, fallback=dict)
    print(
        f"  [OUTPUT] {json.dumps(result_raw, ensure_ascii=False, default=str)[:500] if result_raw else 'None'}"
    )
    print(_SUB)

    # ── dm_narrate ──
    print(f"\n{_SEP}")
    print("  DM Engine: dm_narrate (Phase 6)")
    print(_SEP)

    narrate_req = DMNarrateRequest(
        tick=0,
        plot_brief="The party encounters a strange traveler.",
        dm_instructions=[],
        scene_direction={},
        character_actions=[{"character_id": "alex", "action_type": "explore"}],
    )
    prompt_n = prompts.get_template("dm/dm_narrate.jinja").render(
        plot_brief=narrate_req.plot_brief,
        character_actions=narrate_req.character_actions,
        events=[],
        combat_result=None,
        cast_changes=[],
    )
    print(f"  [INPUT]  plot_brief: {narrate_req.plot_brief}")
    print(f"  [INPUT]  prompt:\n{prompt_n[:300]}...")
    print(_SUB)

    msgs_n = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt_n),
    ]
    result2_raw = await client.call_structured("dm_narrate", None, msgs_n, fallback=dict)
    print(
        f"  [OUTPUT] {json.dumps(result2_raw, ensure_ascii=False, default=str)[:500] if result2_raw else 'None'}"
    )
    print(_SUB)
    print("  DM Engine OK")


async def _test_tick() -> None:
    """全链路：Graph + LLM / Full tick with Graph + LLM."""
    from src.config import load_config
    from src.llm.llm_client import LLMClient

    config = load_config("../config.yaml")
    client = LLMClient(config.llm)
    orch = Orchestrator(llm=client)

    print(f"\n{_SEP}")
    print("  Full Tick: Orchestrator + Graph + LLM")
    print(f"  provider: {config.llm.providers.primary.base_url or '(default)'}")
    print(_SEP)

    result = await orch.run_tick()
    print(f"  [OUTPUT] Tick {result['tick']}")
    print(f"  [OUTPUT] DM narrative: {result.get('narrative', '')}")
    for a in result.get("character_actions", [])[:5]:
        print(f"  [OUTPUT] Act: {a.get('character_id', '?')}({a.get('action_type', '?')})")
    errs = result.get("errors", [])
    if errs:
        print(f"  [OUTPUT] errors: {errs}")
    print(_SUB)
    print("  Full Tick OK")


async def test(args: argparse.Namespace) -> None:
    """LLM 组件诊断 / LLM component diagnostics."""
    run_all = args.test_all or not (args.test_client or args.test_engine or args.test_tick)

    if run_all or args.test_client:
        await _test_client()
    if run_all or args.test_engine:
        await _test_engine()
    if run_all or args.test_tick:
        await _test_tick()


# ═══════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    setup_logging()  # 最优先执行，确保后续所有日志使用 UTF-8 编码
    parser = argparse.ArgumentParser(description="AIGameWorld CLI")
    sub = parser.add_subparsers(dest="command")

    # run 子命令 / run subcommand
    run_parser = sub.add_parser("run", help="Run N ticks")
    run_parser.add_argument("--ticks", type=int, default=5, help="Number of ticks (default: 5)")
    run_parser.add_argument(
        "--db", action="store_true", help="Enable full DB read/write + seed data"
    )
    run_parser.add_argument("--db-path", default="data/world_db.db", help="DB file path")
    run_parser.add_argument("--llm", action="store_true", help="Use real LLM instead of mock")

    # test 子命令（诊断）/ test subcommand (diagnostic)
    test_parser = sub.add_parser("test", help="LLM component diagnostics")
    test_parser.add_argument(
        "--client", dest="test_client", action="store_true", help="Test LLMClient only"
    )
    test_parser.add_argument(
        "--engine", dest="test_engine", action="store_true", help="Test DM engine"
    )
    test_parser.add_argument(
        "--tick", dest="test_tick", action="store_true", help="Test full tick with LLM"
    )
    test_parser.add_argument(
        "--all", dest="test_all", action="store_true", help="Test everything (default)"
    )

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(run(args))
    elif args.command == "test":
        asyncio.run(test(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
