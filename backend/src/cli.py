"""CLI 入口 / CLI entry point.

用法 / Usage:
  aw -i                                          # 交互式模式 / Interactive REPL
  aw -i --pack-id forgotten_realms               # 交互式 + 指定 pack
  aw run --ticks 5                               # 纯 mock，不写 DB / mock only
  aw run --ticks 3 --db --pack-id forgotten_realms --llm  # LLM + pack
  aw import worlds/forgotten_realms --db data/world_db.db    # 导入 pack / import pack
  aw serve                                       # 一键启动前后端 / Start backend + frontend
  aw serve --port 8000 --frontend-port 5173      # 指定端口 / custom ports
  aw view                                        # 启动 DB 查看器 / Start DB viewer
  aw view --port 8080                            # 指定端口 / custom port
  aw test --all                                  # LLM 诊断 / diagnostics
"""

import argparse
import asyncio
import contextlib
import json
import os
import shlex
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from src.orchestrator import Orchestrator
from src.repository.actor_repo import ActorRepo
from src.repository.dm_record_repo import DMRecordRepo
from src.repository.event_repo import TickEventRepo
from src.repository.memory_repo import MemoryRepo
from src.repository.message_repo import TickMessageRepo
from src.repository.pc_repo import PcRepo
from src.repository.scene_repo import SceneRepo
from src.repository.world_repo import WorldRepo
from src.storage.chroma_client import ChromaClient
from src.storage.sqlite_client import SQLiteClient
from src.utils.logging import setup_logging

# ═══════════════════════════════════════════════════════════════
# 种子数据 / Seed data
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# 输出 / Output
# ═══════════════════════════════════════════════════════════════


def _print_tick(
    tick: int,
    narrative: str,
    decisions: list,
    tick_events: list,
    errors: list,
    db_info: str = "",
) -> None:
    print(f"{'=' * 60}")
    header = f"[Tick {tick}]" + (f"  {db_info}" if db_info else "")
    print(header)
    if narrative:
        print(f"  [DM] {narrative}")
    for a in decisions:
        cid = a.get("pc_id", "?")
        atype = a.get("action_type", a.get("type", "?"))
        desc = a.get("reasoning", a.get("description", ""))
        print(f"  [Act] {cid}({atype}): {desc}")
    for ev in tick_events[:3]:
        print(f"  [Evt] {ev.get('type', '?')}: {ev.get('description', '')[:80]}")
    if errors:
        print(f"  [Err] {[e[:60] for e in errors]}")


# ═══════════════════════════════════════════════════════════════
# run — 单次运行 / one-shot run
# ═══════════════════════════════════════════════════════════════


async def run(args: argparse.Namespace) -> None:
    """CLI 参数 → _do_run / CLI args → _do_run."""
    from src.config import load_config

    config = load_config(str(Path(__file__).parent.parent.parent / "config.yaml"))
    db_path = args.db_path or config.db_name
    await _do_run(
        ticks=args.ticks,
        db_path=db_path,
        pack_id=args.pack_id or None,
        use_llm=args.llm,
        mock_dataset=args.mock_dataset or "",
    )


async def _get_first_world_id(db: SQLiteClient) -> str:
    rows = await db.fetch_all("SELECT id FROM worlds LIMIT 1")
    return rows[0]["id"] if rows else "default"


async def _do_run(
    ticks: int = 5,
    db_path: str = "data/world_db.db",
    pack_id: str | None = None,
    use_llm: bool = False,
    mock_dataset: str = "",
) -> None:
    """核心运行逻辑——始终使用真实 DB 数据，LLM 默认 mock 模式."""
    n = ticks
    llm_mode = "LLM" if use_llm else "LLM(mock)"
    print(f"AIGameWorld -- {llm_mode} | DB={pack_id or 'world_db.db'}")
    print(f"Running {n} tick(s)...\n")

    # -- DB：始终初始化 + 加载 pack 数据 / Always init DB and load pack data
    db = SQLiteClient(db_path)
    await db.connect()
    await db.init_schema()
    print("  [DB] initialized")

    pc_repo = PcRepo(db)
    actor_repo = ActorRepo(db)
    record_repo = DMRecordRepo(db)

    if pack_id:
        pcs = await pc_repo.load_all(pack_id)
        actors = await actor_repo.load_all(pack_id)
        print(f"  [DB] pack_id={pack_id}")
    else:
        pcs = await pc_repo.load_all()
        actors = await actor_repo.load_all()
        print("  [DB] no pack_id specified")
    print(f"  [DB] Loaded {len(pcs)} PCs, {len(actors)} Actors")

    repos = {
        "dm_record": record_repo,
        "char": pc_repo,
        "scene": SceneRepo(db),
        "world": WorldRepo(db),
        "event": TickEventRepo(db),
        "message": TickMessageRepo(db),
    }

    # -- LLM：创建客户端（--llm 覆盖 mock 开关，dataset 默认读 config.yaml）
    from src.config import load_config
    from src.llm.llm_client import LLMClient

    config = load_config(str(Path(__file__).parent.parent.parent / "config.yaml"))
    _use_mock = not use_llm if use_llm else config.llm_mock
    _dataset = mock_dataset or config.mock_dataset
    config.runtime.llm_mock = _use_mock
    config.runtime.mock_dataset = _dataset
    llm = LLMClient(config)
    if use_llm:
        provider_url = config.llm.providers.primary.base_url or "(default)"
        print(f"  [LLM] provider: {provider_url}")
    elif _use_mock:
        print(f"  [LLM] mock mode dataset={_dataset}")

    chroma = ChromaClient(persist_path="data/chroma")
    repos["memory"] = MemoryRepo(chroma=chroma, sqlite=db)
    await repos["memory"].initialize()

    # -- Tick 循环 / Tick loop
    world_id = pack_id or await _get_first_world_id(db)
    orch = Orchestrator(llm=llm, repos=repos)

    for _ in range(n):
        result = await orch.run_tick(world_id)
        tick = result["tick"]
        narrative = result.get("narrative", "")
        tick_events = result.get("tick_events", [])
        decisions = result.get("pc_decisions", [])

        _print_tick(tick, narrative, decisions, tick_events, [], db_info=f"[DB] ticks {tick}")

    # -- 收尾：统计 + 关闭 DB / cleanup: stats + close DB
    print(f"{'=' * 60}")
    if db:
        records_count = len(await db.fetch_all("SELECT id FROM dm_records"))
        print(f"Done. DB: dm_records={records_count}")
        await db.close()
    else:
        print(f"Done. {n} tick(s) completed.")


# ═══════════════════════════════════════════════════════════════
# test — LLM 诊断 / LLM diagnostics
# ═══════════════════════════════════════════════════════════════

_SEP = "=" * 60
_SUB = "-" * 40


async def _test_client() -> None:
    """测试 LLMClient 基础调用 / Test LLMClient basic call."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.config import load_config
    from src.llm.llm_client import LLMClient

    config = load_config(str(Path(__file__).parent.parent.parent / "config.yaml"))
    client = LLMClient(config)

    print(f"\n{_SEP}")
    print("  LLMClient 基础调用测试 / Basic Call Test")
    print(f"  provider: {config.llm.providers.primary.base_url or '(default)'}")
    print(_SEP)

    msgs = [SystemMessage(content="Reply in one word."), HumanMessage(content="Hello")]
    print(f"  [INPUT]  tick_messages: {[m.content[:30] for m in msgs]}")
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

    config = load_config(str(Path(__file__).parent.parent.parent / "config.yaml"))
    client = LLMClient(config)
    prompts = Environment(loader=FileSystemLoader(Path(__file__).parent / "prompts"))

    # ── dm_create ──
    print(f"\n{_SEP}")
    print("  DM Engine: dm_create (Phase 1)")
    print(_SEP)

    create_req = DMCreateRequest(tick=0, plot_brief="")
    system_prompt = prompts.get_template("dm/_dm_system.jinja").render()
    prompt = prompts.get_template("dm/dm_create.jinja").render(
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
        hints=[],
    )
    prompt_n = prompts.get_template("dm/dm_narrate.jinja").render(
        plot_brief=narrate_req.plot_brief,
        hints=narrate_req.hints,
        events=[],
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

    config = load_config(str(Path(__file__).parent.parent.parent / "config.yaml"))
    client = LLMClient(config)
    orch = Orchestrator(llm=client)
    world_id = config.world.default_pack

    print(f"\n{_SEP}")
    print("  Full Tick: Orchestrator + Graph + LLM")
    print(f"  provider: {config.llm.providers.primary.base_url or '(default)'}")
    print(_SEP)

    result = await orch.run_tick(world_id)
    print(f"  [OUTPUT] Tick {result['tick']}")
    print(f"  [OUTPUT] DM narrative: {result.get('narrative', '')}")
    for a in result.get("pc_decisions", [])[:5]:
        print(f"  [OUTPUT] Act: {a.get('pc_id', '?')}({a.get('action_type', '?')})")
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
# import — world-pack → DB / YAML → Domain Model → DB
# ═══════════════════════════════════════════════════════════════


async def import_world(args: argparse.Namespace) -> None:
    """导入 world-pack（实例 YAML 合集）到 SQLite + (可选) ChromaDB."""
    from src.storage.chroma_client import ChromaClient
    from src.storage.sqlite_client import SQLiteClient
    from src.world_pack_loader.loader import WorldLoader

    pack_dir: Path = args.path
    if not pack_dir.exists():
        print(f"Error: world-pack directory not found: {pack_dir}")
        return

    print(f"Importing world-pack from {pack_dir} ...")

    # 初始化数据库 / Init database
    db = SQLiteClient(str(args.db))
    await db.connect()
    await db.init_schema()

    # 可选 ChromaDB / Optional vector DB
    chroma = None
    if args.chroma:
        chroma = ChromaClient(str(args.chroma))

    # 加载 world-pack / Load world-pack
    loader = WorldLoader(db, chroma)
    counts = await loader.load(pack_dir)
    await db.commit()

    print(f"[OK] Imported: {counts}")
    print(f"     SQLite: {args.db}")
    if args.chroma:
        print(f"     ChromaDB: {args.chroma}")

    await db.close()


# ═══════════════════════════════════════════════════════════════
# shell — 交互式 REPL / interactive REPL（逐参数提示）
# ═══════════════════════════════════════════════════════════════


@dataclass
class ShellState:
    """交互式 shell 状态 / Interactive shell state."""

    pack_id: str = ""
    db_path: str = "data/world_db.db"
    use_llm: bool = False
    use_db: bool = True


_SHELL_HELP = """╔══════════════════════════════════════════════════════╗
║  AIGameWorld Shell                                   ║
╠══════════════════════════════════════════════════════╣
║  import <dir>    导入 world-pack 到 DB               ║
║  run [n]         运行 n 个 tick（默认 5）             ║
║  pack <id>       设置/查看当前 pack_id                ║
║  llm on|off      开关 LLM 模式                       ║
║  db on|off       开关 DB 模式                        ║
║  db-path <path>  设置 DB 文件路径                     ║
║  show            显示当前设置 + DB 统计               ║
║  list            列出 DB 中所有 pack                  ║
║  clear           清空运行时数据 (tick_events/narratives)    ║
║  help|?          显示帮助                             ║
║  exit|quit       退出                                 ║
╚══════════════════════════════════════════════════════╝"""


async def _shell_import(state: ShellState, pack_dir: str) -> None:
    """Shell 内导入 pack / Import pack from shell."""
    path = Path(pack_dir)
    if not path.exists():
        print(f"  Error: directory not found: {path}")
        return
    db = SQLiteClient(state.db_path)
    await db.connect()
    await db.init_schema()
    loader = __import__("src.world_pack_loader.loader", fromlist=["WorldLoader"]).WorldLoader(db)
    counts = await loader.load(path)
    await db.commit()
    await db.close()
    state.pack_id = path.name
    print(f"  [OK] Imported: {counts}")
    if counts:
        print(f"  [OK] pack_id set to '{state.pack_id}'")


async def _shell_show(state: ShellState) -> None:
    """显示当前状态 / Show current state."""
    print("━" * 50)
    print(f"  pack_id  : {state.pack_id or '(not set)'}")
    print(f"  DB path  : {state.db_path}  (DB: {'ON' if state.use_db else 'OFF'})")
    print(f"  LLM      : {'ON' if state.use_llm else 'OFF'}")
    # DB 统计 / DB stats
    try:
        db = SQLiteClient(state.db_path)
        await db.connect()
        for label, table in [
            ("PCs", "player_characters"),
            ("Actors", "actors"),
            ("Scenes", "scenes"),
            ("Items", "items"),
            ("Story", "story"),
            ("Events", "tick_events"),
        ]:
            # 表名来自常量列表，非用户输入 / table names are constants, not user input
            rows = await db.fetch_all(f"SELECT COUNT(*) as c FROM {table}")  # noqa: S608
            count = rows[0]["c"] if rows else 0
            print(f"  {label:12s}: {count:4d}")
        await db.close()
    except Exception as e:
        print(f"  DB: (error) {e}")
    print("━" * 50)


async def _shell_list_packs(state: ShellState) -> None:
    """列出 DB 中所有 pack / List all packs in DB."""
    try:
        db = SQLiteClient(state.db_path)
        await db.connect()
        packs: set[str] = set()
        for table in [
            "player_characters",
            "actors",
            "scenes",
            "items",
            "scene_objects",
        ]:
            try:
                # 表名来自常量列表，非用户输入 / table names are constants
                rows = await db.fetch_all(
                    f"SELECT DISTINCT pack_id FROM {table} WHERE pack_id != ''"  # noqa: S608
                )
                for r in rows:
                    packs.add(r["pack_id"])
            except Exception as e:
                print(f"    (warning: {e})")
        await db.close()
        if packs:
            print("  Available packs:")
            for p in sorted(packs):
                marker = " <-- current" if p == state.pack_id else ""
                print(f"    {p}{marker}")
        else:
            print("  (no packs in DB)")
    except Exception as e:
        print(f"  Error: {e}")


async def _shell_clear() -> None:
    """清空运行时数据 / Clear runtime data."""
    db = SQLiteClient("data/world_db.db")
    await db.connect()
    await db.execute("DELETE FROM tick_events")
    await db.execute("DELETE FROM dm_records")
    await db.execute("DELETE FROM story_summaries")
    await db.execute("UPDATE worlds SET data_tick = 0, display_tick = 0")
    await db.commit()
    await db.close()
    print("  [OK] Cleared tick_events, dm_records, story_summaries, reset world ticks")


def _show_current(state: ShellState) -> None:
    """显示当前关键参数 / Show current key parameters."""
    print(
        f"  pack_id={state.pack_id or '(none)'}  db={'ON' if state.use_db else 'OFF'}  llm={'ON' if state.use_llm else 'OFF'}  path={state.db_path}"
    )


async def shell(args: argparse.Namespace) -> None:
    """交互式 REPL / Interactive REPL — 分步引导参数输入 / wizard-style parameter prompts."""
    state = ShellState(
        pack_id=args.pack_id or "",
        db_path=args.db_path or "data/world_db.db",
    )
    print(_SHELL_HELP)
    _show_current(state)
    print()

    def _ask(prompt: str, default: str = "") -> str | None:
        """单步输入，返回 None 表示取消 / single input, None = cancel."""
        try:
            v = input(f"    {prompt} [{default}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        return v if v else default

    async def _wizard_run() -> None:
        """分步引导 run 参数 / guided run wizard."""
        print("  --- Run Wizard ---")
        pack = _ask("pack_id", state.pack_id or "")
        if pack is None:
            return
        if pack:
            state.pack_id = pack
        t = _ask("ticks", "5")
        if t is None:
            return
        llm_mode = _ask("LLM (on/off)", "on" if state.use_llm else "off")
        if llm_mode is None:
            return
        state.use_llm = llm_mode.lower() in ("on", "1", "yes", "y")
        db_mode = _ask("DB (on/off)", "on" if state.use_db else "off")
        if db_mode is None:
            return
        state.use_db = db_mode.lower() in ("on", "1", "yes", "y")
        print()

        await _do_run(
            ticks=int(t) if t else 5,
            db_path=state.db_path,
            pack_id=state.pack_id or None,
            use_llm=state.use_llm,
        )

    while True:
        try:
            raw = input("aw> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nexit")
            break
        if not raw:
            continue

        parts = shlex.split(raw)
        cmd = parts[0].lower()
        inline_arg = parts[1] if len(parts) > 1 else None

        try:
            if cmd in ("exit", "quit"):
                break
            elif cmd in ("help", "?"):
                print(_SHELL_HELP)
            elif cmd == "import":
                arg = inline_arg or _ask("pack_dir", "")
                if arg:
                    await _shell_import(state, arg)
            elif cmd == "run":
                if inline_arg:
                    # 行内快捷模式 / inline shortcut
                    await _do_run(
                        ticks=int(inline_arg),
                        db_path=state.db_path,
                        pack_id=state.pack_id or None,
                        use_llm=state.use_llm,
                    )
                else:
                    await _wizard_run()
            elif cmd == "pack":
                if inline_arg:
                    state.pack_id = inline_arg
                else:
                    state.pack_id = _ask("pack_id", state.pack_id) or state.pack_id
                print(f"  pack_id = '{state.pack_id or '(not set)'}'")
            elif cmd == "llm":
                v = (inline_arg or _ask("on/off", "on" if state.use_llm else "off") or "").lower()
                if v in ("on", "off"):
                    state.use_llm = v == "on"
                print(f"  LLM = {'ON' if state.use_llm else 'OFF'}")
            elif cmd == "db":
                v = (inline_arg or _ask("on/off", "on" if state.use_db else "off") or "").lower()
                if v in ("on", "off"):
                    state.use_db = v == "on"
                print(f"  DB = {'ON' if state.use_db else 'OFF'}")
            elif cmd == "db-path":
                arg = inline_arg or _ask("path", state.db_path)
                if arg:
                    state.db_path = arg
                print(f"  db_path = '{state.db_path}'")
            elif cmd == "show":
                await _shell_show(state)
            elif cmd == "list":
                await _shell_list_packs(state)
            elif cmd == "clear":
                await _shell_clear()
            else:
                print(f"  Unknown: {cmd}  (type 'help' for commands)")
        except ValueError:
            print("  Invalid value")
        except Exception as e:
            print(f"  Error: {e}")

    print("bye.")


# ═══════════════════════════════════════════════════════════════
# main — CLI 入口 / CLI entry
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# serve — 一键启动前后端 / Start backend + frontend dev servers
# ═══════════════════════════════════════════════════════════════


async def serve(args: argparse.Namespace) -> None:
    """启动后端 FastAPI + 前端 Vite 开发服务器 / Start backend FastAPI + frontend Vite dev server."""
    project_root = Path(__file__).parent.parent  # backend/
    frontend_dir = project_root.parent / "frontend"  # AIGameWorld/frontend/

    processes: list[subprocess.Popen] = []

    def cleanup() -> None:
        """关闭所有子进程 / Terminate all child processes."""
        print("\n[serve] Shutting down...")
        for p in processes:
            with contextlib.suppress(Exception):
                p.terminate()
        print("[serve] All servers stopped. Goodbye!")

    # 信号处理 / Signal handling — Ctrl+C 时清理子进程
    def signal_handler(_sig: int, _frame: object) -> None:
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # ── 1. 启动后端 / Start backend ──
        backend_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "src.server:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--log-level",
            "info",
        ]
        print(
            f"[serve] Starting backend: uvicorn src.server:app --host {args.host} --port {args.port}"
        )
        backend_proc = subprocess.Popen(  # noqa: S603
            backend_cmd,
            cwd=str(project_root),
            env={**os.environ, "PYTHONPATH": str(project_root)},
        )
        processes.append(backend_proc)
        await asyncio.sleep(2)  # 等后端启动 / Wait for backend

        # 检查后端是否启动成功 / Check backend health
        if backend_proc.poll() is not None:
            print("[serve] ERROR: Backend failed to start!")
            cleanup()
            return

        print(f"[serve] ✓ Backend running at http://localhost:{args.port}")
        print(f"[serve]   API: http://localhost:{args.port}/api/world/forgotten_realms/state")

        print(f"[serve]   Viewer: http://localhost:{args.port}/view")

        # ── 2. 启动前端 / Start frontend ──
        if not args.no_frontend and frontend_dir.exists():
            print(f"[serve] Starting frontend: vite --port {args.frontend_port}")
            frontend_cmd = [
                "npx",
                "vite",
                "--port",
                str(args.frontend_port),
                "--host",
                args.host,
            ]
            # Windows 下需要 shell=True / Need shell on Windows
            frontend_proc = subprocess.Popen(  # noqa: S603
                frontend_cmd,
                cwd=str(frontend_dir),
                shell=(os.name == "nt"),
            )
            processes.append(frontend_proc)
            await asyncio.sleep(1)

            if frontend_proc.poll() is not None:
                print("[serve] WARNING: Frontend may have failed to start. Check Node.js/npm.")
                print("[serve]   Run manually: cd frontend && npx vite --port 5173")
            else:
                print(f"[serve] ✓ Frontend running at http://localhost:{args.frontend_port}")
                print(
                    f"[serve]   Game page: http://localhost:{args.frontend_port}/?pack=forgotten_realms"
                )
        elif not frontend_dir.exists():
            print(f"[serve] WARNING: Frontend dir not found at {frontend_dir}, skipping.")
        else:
            print("[serve] Backend only mode (--no-frontend)")

        # ── 3. 打印汇总 / Print summary ──
        print()
        print("=" * 60)
        print("  AIGameWorld 开发服务器已启动 / Dev servers running")
        print("=" * 60)
        print(f"  Backend:  http://localhost:{args.port}")
        if not args.no_frontend and frontend_dir.exists():
            print(f"  Frontend: http://localhost:{args.frontend_port}")
            print(f"  Game:     http://localhost:{args.frontend_port}/?pack=forgotten_realms")
        print(f"  Viewer:   http://localhost:{args.port}/view")
        print()
        print("  按 Ctrl+C 停止所有服务 / Press Ctrl+C to stop")
        print("=" * 60)
        print()

        # ── 4. 保持运行 / Keep alive ──
        while True:
            await asyncio.sleep(1)
            # 检查后端是否崩溃 / Check if backend crashed
            if backend_proc.poll() is not None:
                print("[serve] Backend process exited unexpectedly!")
                cleanup()
                break
            # 检查前端 / Check frontend
            if not args.no_frontend:
                fp = processes[-1] if len(processes) > 1 else None
                if fp and fp.poll() is not None:
                    print("[serve] Frontend process exited. Backend still running.")

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


# ═══════════════════════════════════════════════════════════════
# view — 启动 DB 查看器 / Start DB viewer server
# ═══════════════════════════════════════════════════════════════


async def view_server(args: argparse.Namespace) -> None:
    """启动 DB 查看器 Web 服务 / Start DB viewer web server."""
    project_root = Path(__file__).parent.parent  # backend/
    print(f"[view] Starting DB viewer on http://localhost:{args.port}")
    print(f"[view]   DB: {args.db}")
    print(f"[view]   Home:    http://localhost:{args.port}/view")
    print(f"[view]   Events:  http://localhost:{args.port}/view/global/tick_events")
    print(f"[view]   Items:   http://localhost:{args.port}/view/global/items")
    print()
    print("   按 Ctrl+C 停止 / Press Ctrl+C to stop")

    def signal_handler(_sig: int, _frame: object) -> None:
        print("\n[view] Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.server:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--log-level",
        "info",
    ]
    proc = subprocess.Popen(  # noqa: S603
        cmd, cwd=str(project_root), env={**os.environ, "PYTHONPATH": str(project_root)}
    )
    try:
        while True:
            await asyncio.sleep(1)
            if proc.poll() is not None:
                print("[view] Server stopped.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        with contextlib.suppress(Exception):
            proc.terminate()


def main() -> None:
    from src.config import load_config
    from src.utils.logging import configure_format

    try:
        config = load_config(str(Path(__file__).parent.parent.parent / "config.yaml"))
        configure_format(config.logging.json_format)
        setup_logging(config.logging.level, json_fmt=config.logging.json_format)
    except Exception:
        configure_format(True)
        setup_logging()

    parser = argparse.ArgumentParser(
        prog="aw",
        description="AIGameWorld CLI — DM-driven DND world simulation",
        epilog="示例: aw -i  |  aw run --ticks 5 --db --pack-id forgotten_realms --llm  |  aw serve  |  aw view",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="交互式 REPL / Interactive REPL"
    )
    parser.add_argument("--pack-id", default="", help="Initial pack_id for interactive mode")
    parser.add_argument("--db-path", default="data/world_db.db", help="DB file path")
    sub = parser.add_subparsers(dest="command")

    # run — 单次运行 / one-shot run
    run_parser = sub.add_parser("run", help="Run N ticks")
    run_parser.add_argument("--ticks", type=int, default=5, help="Number of ticks (default: 5)")
    run_parser.add_argument("--db-path", default="", help="DB file path (default: config.yaml)")
    run_parser.add_argument(
        "--pack-id", default="", help="Load pack data from DB (e.g. forgotten_realms)"
    )
    run_parser.add_argument("--llm", action="store_true", help="Use real LLM instead of mock")
    run_parser.add_argument(
        "--mock-dataset", default="", help="Mock dataset name (tavern|combat) / Mock 数据集名称"
    )

    # test — LLM 诊断 / LLM diagnostics
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

    # import — world-pack → DB
    imp_parser = sub.add_parser("import", help="Import world-pack into DB")
    imp_parser.add_argument(
        "path", type=Path, help="World-pack directory path (aw-studio generate output)"
    )
    imp_parser.add_argument(
        "--db", type=Path, default=Path("data/world_db.db"), help="SQLite DB path"
    )
    imp_parser.add_argument(
        "--chroma", type=Path, default=None, help="ChromaDB persist path (optional)"
    )

    # serve — 一键启动前后端 / Start backend + frontend
    serve_parser = sub.add_parser("serve", help="Start backend + frontend dev servers")
    serve_parser.add_argument("--port", type=int, default=8000, help="Backend port (default: 8000)")
    serve_parser.add_argument(
        "--frontend-port", type=int, default=5173, help="Frontend port (default: 5173)"
    )
    serve_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    serve_parser.add_argument("--no-frontend", action="store_true", help="Backend only")

    # view — 启动 DB 查看器 / Start DB viewer
    view_parser = sub.add_parser("view", help="Start DB viewer server")
    view_parser.add_argument("--port", type=int, default=8080, help="Viewer port (default: 8080)")
    view_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    view_parser.add_argument(
        "--db", default="data/world_db.db", help="DB path (default: data/world_db.db)"
    )

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(shell(args))
    elif args.command == "run":
        asyncio.run(run(args))
    elif args.command == "test":
        asyncio.run(test(args))
    elif args.command == "import":
        asyncio.run(import_world(args))
    elif args.command == "serve":
        asyncio.run(serve(args))
    elif args.command == "view":
        asyncio.run(view_server(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
