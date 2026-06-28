"""CLI 入口 / CLI entry point.

用法:
  python -m src.cli run --ticks 5          # 纯 mock，不写 DB
  python -m src.cli run --ticks 3 --db     # 全链路：DB 读写
"""

import asyncio
import argparse
from pathlib import Path

from src.engine.orchestrator import Orchestrator
from src.storage.sqlite_client import SQLiteClient
from src.repository.character_repo import CharacterRepo
from src.domain import PlayerCharacter, Actor, Location, Attributes, CombatStats, Equipment, CharacterArc


async def run_full(db_path: str, n: int) -> None:
    """全链路：DB 初始化 → 种子数据 → tick 循环 → 写 DB."""
    print("Phase 1 — Full Loop: Graph + SQLite")
    print(f"DB: {db_path}")
    print(f"Running {n} tick(s)...\n")

    # ── ① DB 初始化 ──
    db = SQLiteClient(db_path)
    await db.connect()
    await db.init_schema()
    repo = CharacterRepo(db)
    print("  💾 DB initialized (15 tables)")

    # ── ② 种子 demo 角色 ──
    pcs = _seed_pcs()
    for pc in pcs:
        await repo.save_pc(pc)
    print(f"  💾 Seeded {len(pcs)} PCs: {[p.name for p in pcs]}")

    actors = _seed_actors()
    for a in actors:
        await repo.save_actor(a)
    print(f"  💾 Seeded {len(actors)} Actors: {[a.name for a in actors]}")
    await db.commit()

    # ── ③ Tick 循环 ──
    orch = Orchestrator()
    for i in range(n):
        # 从 DB 加载当前角色
        loaded_pcs = await repo.load_pcs()
        loaded_actors = await repo.load_actors()

        result = await orch.run_tick()
        tick = result["tick"]
        narrative = result.get("narrative", "")
        events = result.get("events", [])
        actions = result.get("character_actions", [])
        errors = result.get("errors", [])

        # ④ 写 DB：narratives + events + world_meta
        if narrative:
            await db.execute(
                "INSERT INTO narratives (tick, content) VALUES (?, ?)",
                (tick, narrative),
            )
        for ev in events:
            await db.execute(
                "INSERT INTO events (id, tick, seq, type, source, data_json) VALUES (?, ?, ?, ?, ?, ?)",
                (f"evt_{tick}_{events.index(ev)}", tick, events.index(ev),
                 ev.get("type", "?"), "dm", "{}"),
            )
        await db.execute(
            "INSERT OR REPLACE INTO world_meta (key, value) VALUES (?, ?)",
            ("current_tick", str(tick)),
        )
        await db.commit()

        # ── 输出 ──
        print(f"{'='*60}")
        print(f"[Tick {tick}]  💾 DB: {len(loaded_pcs)} PCs + {len(loaded_actors)} Actors loaded")
        if narrative:
            print(f"  📖 {narrative}")
        for a in actions:
            print(f"  🎭 {a.get('character_id','?')}({a.get('type','?')}): {a.get('description','')}")
        for ev in events[:3]:
            print(f"  ⚡ {ev.get('type','?')}: {ev.get('description','')[:80]}")
        if errors:
            print(f"  ❌ Errors: {errors}")

    # ── ⑤ 验证 DB 读 ──
    tick_row = await db.fetch_one("SELECT value FROM world_meta WHERE key = 'current_tick'")
    narrative_count = len(await db.fetch_all("SELECT id FROM narratives"))
    print(f"{'='*60}")
    print(f"Done. DB state: tick={tick_row['value'] if tick_row else '?'}, "
          f"narratives={narrative_count}, PCs={len(pcs)}, Actors={len(actors)}")

    await db.close()


async def run_mock(n: int) -> None:
    """纯 mock，不写 DB."""
    orch = Orchestrator()
    print("Phase 1 — Mock Loop (no DB)")
    print(f"Running {n} tick(s)...\n")

    for i in range(n):
        result = await orch.run_tick()
        tick = result["tick"]
        narrative = result.get("narrative", "")
        events = result.get("events", [])
        actions = result.get("character_actions", [])
        errors = result.get("errors", [])

        print(f"{'='*60}")
        print(f"[Tick {tick}]")
        if narrative:
            print(f"  📖 {narrative}")
        for a in actions:
            print(f"  🎭 {a.get('character_id','?')}({a.get('type','?')}): {a.get('description','')}")
        for ev in events[:3]:
            print(f"  ⚡ {ev.get('type','?')}: {ev.get('description','')[:80]}")
        if errors:
            print(f"  ❌ Errors: {errors}")

    print(f"{'='*60}")
    print(f"Done. {n} tick(s) completed.")


# ── 种子数据 ──
def _seed_pcs() -> list[PlayerCharacter]:
    return [
        PlayerCharacter(
            id="alex", name="Alex", role="fighter", race="human",
            scene_id="tavern", location=Location(scene_id="tavern"),
            attributes=Attributes(strength=16, dexterity=12, constitution=14, intelligence=10, wisdom=10, charisma=12),
            combat=CombatStats(hp=28, max_hp=28, ac=16, initiative=2, attack_bonus=5),
            character_arc=CharacterArc(growth_line="prove_worth", inner_conflict="recklessness"),
        ),
        PlayerCharacter(
            id="maya", name="Maya", role="rogue", race="elf",
            scene_id="tavern", location=Location(scene_id="tavern"),
            attributes=Attributes(strength=10, dexterity=18, constitution=12, intelligence=14, wisdom=12, charisma=14),
            combat=CombatStats(hp=20, max_hp=20, ac=14, initiative=4, attack_bonus=6),
            character_arc=CharacterArc(growth_line="find_purpose", inner_conflict="trust"),
        ),
    ]


def _seed_actors() -> list[Actor]:
    return [
        Actor(
            id="innkeeper", name="Greta", role="innkeeper", race="dwarf",
            scene_id="tavern", location=Location(scene_id="tavern"),
            attributes=Attributes(strength=12, dexterity=8, constitution=14, intelligence=10, wisdom=14, charisma=16),
            personality="Warm but sharp-eyed. Knows everyone's secrets.",
            functions=["dialogue", "merchant"],
        ),
        Actor(
            id="guard", name="Sergeant Cole", role="town_guard", race="human",
            scene_id="town_square", location=Location(scene_id="town_square"),
            attributes=Attributes(strength=14, dexterity=10, constitution=14, intelligence=10, wisdom=12, charisma=10),
            combat=CombatStats(hp=22, max_hp=22, ac=15, initiative=1, attack_bonus=4),
            personality="Stern but fair. Served the town for 20 years.",
            functions=["guard", "dialogue"],
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="AIGameWorld CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run N ticks")
    run_parser.add_argument("--ticks", type=int, default=5)
    run_parser.add_argument("--db", action="store_true", help="Enable full DB read/write loop")

    args = parser.parse_args()

    if args.command == "run":
        if args.db:
            asyncio.run(run_full("data/world_state.db", args.ticks))
        else:
            asyncio.run(run_mock(args.ticks))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
