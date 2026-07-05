"""结构化日志辅助 / Structured logging helpers.

对齐业界推荐：
- extra 始终包含 event 字段
- latency_ms 统一命名
- 性能日志 → logs/perf.log，业务日志 → logs/app.log
- 控制台输出类别由 config.yaml logging.console 开关控制
- get_logger(__name__) 自动去除 src. 前缀
- JSON 格式输出，兼容 ELK/Splunk
"""

import contextlib
import functools
import logging
import sys
import time as _time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, cast

from pythonjsonlogger.json import JsonFormatter

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_json_format: bool = True

# 模块路径 → 类别名 转换，对齐 config.yaml console 下的 key
_MODULE_RENAME: dict[str, str] = {
    "graph.orchestrator": "orchestrator",
    "repository": "repo",
    "services": "service",
    "server": "main",
    "world_pack_loader": "loader",
}

# 性能日志 logger 名
_PERF_LOGGERS = {"performance"}

# 控制台开关，category_name → bool
_console_toggles: dict[str, bool] = {}


def get_logger(name: str) -> logging.Logger:
    """获取 logger，去掉 src. 前缀并转换模块路径为类别名.

    services.* → service.*
    repository.* → repo.*
    world_pack_loader.* → loader.*
    graph.orchestrator → orchestrator
    """
    name = name.removeprefix("src.")
    # 全路径匹配优先
    if name in _MODULE_RENAME:
        return logging.getLogger(_MODULE_RENAME[name])
    # 首段替换
    parts = name.split(".")
    if parts[0] in _MODULE_RENAME:
        parts[0] = _MODULE_RENAME[parts[0]]
    return logging.getLogger(".".join(parts))


def configure_console(toggles: dict[str, bool] | None) -> None:
    """设置控制台开关，key=类别名 value=True/False."""
    _console_toggles.clear()
    if toggles:
        _console_toggles.update(toggles)


def configure_format(json_fmt: bool = True) -> None:
    """设置日志格式：True=JSON, False=文本."""
    globals()["_json_format"] = json_fmt


# ═══════════════════════════════════════════════════════════════
# JSON Formatter / 结构化 JSON 格式化
# ═══════════════════════════════════════════════════════════════

_TEXT_FMT = "%(asctime)s | %(name)-24s | %(levelname)-8s | %(message)s"
_JSON_FMT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def _make_formatter() -> logging.Formatter:
    if _json_format:
        return JsonFormatter(
            _JSON_FMT,
            datefmt="%Y-%m-%dT%H:%M:%S",
            json_ensure_ascii=False,
        )
    return logging.Formatter(fmt=_TEXT_FMT, datefmt="%Y-%m-%d %H:%M:%S")


class _PerfFilter(logging.Filter):
    def filter(self, record):
        return record.name in _PERF_LOGGERS


class _BizFilter(logging.Filter):
    def filter(self, record):
        return record.name not in _PERF_LOGGERS


class _ConsoleFilter(logging.Filter):
    def filter(self, record):
        if not _console_toggles:
            return True
        name = record.name
        for cat, enabled in _console_toggles.items():
            if enabled and (name == cat or name.startswith(cat + ".")):
                return True
        return False


def setup_logging(level: str = "INFO") -> None:
    """初始化日志——控制台可配置 + 文件分流 + JSON 格式."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            # reconfigure 仅在支持的平台可用 / reconfigure may not exist on all platforms
            if hasattr(stream, "reconfigure"):
                # pyright 将 stream 推断为 TextIO，实际为 io.TextIOWrapper / pyright sees TextIO, runtime is TextIOWrapper
                cast(Any, stream).reconfigure(encoding="utf-8", errors="replace")

    root = logging.getLogger()
    root.setLevel(log_level)
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        return

    fmt: logging.Formatter = _make_formatter()

    # ── 控制台：按类别过滤 ──
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(log_level)
    console.setFormatter(fmt)
    console.addFilter(_ConsoleFilter())
    root.addHandler(console)

    # ── 性能日志文件 ──
    perf_file = RotatingFileHandler(
        str(_LOG_DIR / "perf.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    perf_file.setLevel(logging.DEBUG)
    perf_file.setFormatter(fmt)
    perf_file.addFilter(_PerfFilter())
    root.addHandler(perf_file)

    # ── 业务日志文件 ──
    biz_file = RotatingFileHandler(
        str(_LOG_DIR / "app.log"),
        maxBytes=50 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    biz_file.setLevel(logging.DEBUG)
    biz_file.setFormatter(fmt)
    biz_file.addFilter(_BizFilter())
    root.addHandler(biz_file)

    for noisy in (
        "httpx",
        "httpcore",
        "chromadb",
        "urllib3",
        "openai",
        "langchain",
        "langchain_openai",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ═══════════════════════════════════════════════════════════════
# 性能日志 / Performance logs → logger: performance / tick
# ═══════════════════════════════════════════════════════════════


def log_phase(event: str, tick: int, elapsed: float | None = None, **extra) -> None:
    data = {"event": event, "tick": tick, **extra}
    if elapsed is not None:
        data["latency_ms"] = round(elapsed * 1000, 1)
    logging.getLogger("performance").info(f"[performance] {event} tick={tick}", extra=data)


def log_node(name: str, tick: int, latency_ms: float, **extra) -> None:
    logging.getLogger("performance").info(
        f"[performance] {name} tick={tick} {latency_ms}ms",
        extra={"event": name, "tick": tick, "latency_ms": latency_ms, **extra},
    )


# ═══════════════════════════════════════════════════════════════
# 业务日志 / Business logs
# ═══════════════════════════════════════════════════════════════


def log_llm(purpose: str, action: str, elapsed: float, extra: dict | None = None) -> None:
    data = {
        "event": f"llm.{purpose}",
        "purpose": purpose,
        "action": action,
        "latency_ms": round(elapsed * 1000, 1),
    }
    if extra:
        data.update(extra)
    logger = logging.getLogger("llm")
    if action == "error":
        logger.error(f"[llm] {purpose} 失败", extra=data)
    else:
        logger.info(f"[llm] {purpose} ok", extra=data)


def log_api(action: str, world_id: str, **extra) -> None:
    logging.getLogger("api").info(
        f"[api] {action} world={world_id}",
        extra={"event": f"api.{action}", "action": action, "world_id": world_id, **extra},
    )


def log_msg(op: str, tick_message_id: str, tick: int, **extra) -> None:
    logging.getLogger("service").info(
        f"[service] msg.{op} id={tick_message_id} tick={tick}",
        extra={
            "event": f"service.msg.{op}",
            "op": op,
            "tick_message_id": tick_message_id,
            "tick": tick,
            **extra,
        },
    )


def log_db(table: str, op: str, rows: int = 0, **extra) -> None:
    logging.getLogger("storage").info(
        f"[storage] {table} {op} rows={rows}",
        extra={"event": f"storage.{table}.{op}", "table": table, "op": op, "rows": rows, **extra},
    )


def log_graph(node: str, tick: int, latency_ms: float | None = None, **extra) -> None:
    data = {"event": f"graph.{node}", "node": node, "tick": tick, **extra}
    if latency_ms is not None:
        data["latency_ms"] = latency_ms
    logging.getLogger("graph").info(f"[graph] {node} tick={tick}", extra=data)


def log_svc(svc: str, tick: int, **extra) -> None:
    logging.getLogger("svc").info(
        f"[svc] {svc} tick={tick}",
        extra={"event": f"svc.{svc}", "svc": svc, "tick": tick, **extra},
    )


def log_eng(eng: str, tick: int, **extra) -> None:
    logging.getLogger("eng").info(
        f"[eng] {eng} tick={tick}",
        extra={"event": f"eng.{eng}", "eng": eng, "tick": tick, **extra},
    )


def log_repo(repo: str, op: str, **extra) -> None:
    logging.getLogger("repo").info(
        f"[repo] {repo}.{op}",
        extra={"event": f"repo.{repo}.{op}", "repo": repo, "op": op, **extra},
    )


# ═══════════════════════════════════════════════════════════════
# 全链路日志装饰器
# ═══════════════════════════════════════════════════════════════


def trace_node(name: str = ""):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            node_name = name or func.__name__
            tick = 0
            if args and isinstance(args[0], dict):
                tick = args[0].get("tick", 0)
            t0 = _time.monotonic()
            try:
                result = await func(*args, **kwargs)
                latency_ms = round((_time.monotonic() - t0) * 1000, 1)
                log_node(
                    node_name, tick, latency_ms, status="ok", output=_node_out(node_name, result)
                )
                return result
            except Exception:
                latency_ms = round((_time.monotonic() - t0) * 1000, 1)
                log_node(node_name, tick, latency_ms, status="error")
                raise

        return wrapper

    return decorator


def _node_out(name: str, result: object) -> dict:
    """提取节点返回值关键字段."""
    if not isinstance(result, dict):
        return {}
    out: dict[str, object] = {}
    if name in ("msg.create",):
        out["tick_message_id"] = result.get("tick_message_id", "")
    elif name in ("dm.create",):
        out["scene_id"] = result.get("scene_id", "")
        out["hints"] = len(result.get("hints", []))
        brief = result.get("plot_brief", "")
        if isinstance(brief, str):
            out["plot_brief"] = brief[:80]
    elif name in ("scene.build",):
        info = result.get("scene_info", {})
        out["scene_id"] = info.get("scene", {}).get("id", "")
        out["pcs"] = len(info.get("pcs", []))
        out["actors"] = len(info.get("actors", []))
        out["objects"] = len(info.get("scene_objects", []))
    elif name in ("pc.decide",):
        decs = result.get("pc_decisions", [])
        out["decisions"] = len(decs)
        out["actions"] = [d.get("type") for d in decs[:5]]
    elif name in ("pc.act",):
        acts = result.get("pending_actions", [])
        out["actions"] = len(acts)
        out["types"] = [a.get("action_type") for a in acts[:5]]
    elif name in ("dm.narrate",):
        narrative = result.get("narrative", "")
        if isinstance(narrative, str):
            out["narrative_len"] = len(narrative)
    return out
