"""Structured logging configuration.

Best practices aligned with observability standards:
- Single, complete configuration via dictConfig.
- One console handler: stdout, unfiltered, development-friendly.
- Rotating file handlers split by subsystem:
  - app.log     → API, orchestrator, graph, services, repositories, storage
  - engine.log  → LLM calls and game engines (dm, talk, explore, interact, combat, decision)
  - error.log   → ERROR level from any source
  - perf.log    → performance / latency traces
- JSON format for production; plain text format for development.
- All third-party noise suppressed.
"""

import contextlib
import functools
import logging
import logging.config
import sys
import time as _time
from pathlib import Path
from typing import Any, cast

from pythonjsonlogger.json import JsonFormatter

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_json_format: bool = True

# Map module paths to logger names used in config.yaml console toggles
_MODULE_RENAME: dict[str, str] = {
    "graph.orchestrator": "orchestrator",
    "repository": "repo",
    "services": "service",
    "server": "main",
    "world_pack_loader": "loader",
}

# Engine logger prefixes (engine.* and llm.* go to engine.log)
_ENGINE_PREFIXES = ("llm", "llm.", "engine.", "eng", "eng.")

# Performance logger names
_PERF_LOGGERS = {"performance"}


def get_logger(name: str) -> logging.Logger:
    """Return a logger with src. prefix removed and module aliases applied."""
    name = name.removeprefix("src.")
    if name in _MODULE_RENAME:
        return logging.getLogger(_MODULE_RENAME[name])
    parts = name.split(".")
    if parts[0] in _MODULE_RENAME:
        parts[0] = _MODULE_RENAME[parts[0]]
    return logging.getLogger(".".join(parts))


def configure_format(json_fmt: bool = True) -> None:
    """Set whether file/console output should be JSON or plain text."""
    globals()["_json_format"] = json_fmt


# ═══════════════════════════════════════════════════════════════
# Formatters
# ═══════════════════════════════════════════════════════════════

_HUMAN_FMT = "%(asctime)s | %(name)-24s | %(levelname)-8s | %(message)s"
_JSON_FMT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def _make_formatter(json_fmt: bool | None = None) -> logging.Formatter:
    use_json = _json_format if json_fmt is None else json_fmt
    if use_json:
        return JsonFormatter(
            _JSON_FMT,
            datefmt="%Y-%m-%dT%H:%M:%S",
            json_ensure_ascii=False,
        )
    return logging.Formatter(fmt=_HUMAN_FMT, datefmt="%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════
# Filters
# ═══════════════════════════════════════════════════════════════


class _EngineFilter(logging.Filter):
    """Pass records from engine / llm loggers."""

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        return any(name == pfx or name.startswith(pfx) for pfx in _ENGINE_PREFIXES)


class _BusinessFilter(logging.Filter):
    """Pass business records, excluding engine/llm/performance."""

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        if name in _PERF_LOGGERS:
            return False
        return not any(name == pfx or name.startswith(pfx) for pfx in _ENGINE_PREFIXES)


class _PerformanceFilter(logging.Filter):
    """Pass only performance loggers."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name in _PERF_LOGGERS


class _ErrorFilter(logging.Filter):
    """Pass ERROR and above from any logger."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════


def _build_dict_config(level: str, json_fmt: bool) -> dict[str, Any]:
    """Build a complete dictConfig for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    formatter_name = "json" if json_fmt else "human"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": _JSON_FMT,
                "datefmt": "%Y-%m-%dT%H:%M:%S",
                "json_ensure_ascii": False,
            },
            "human": {
                "format": _HUMAN_FMT,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": formatter_name,
                "stream": "ext://sys.stdout",
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": formatter_name,
                "filename": str(_LOG_DIR / "app.log"),
                "maxBytes": 50 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
                "filters": ["business"],
            },
            "engine_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": formatter_name,
                "filename": str(_LOG_DIR / "engine.log"),
                "maxBytes": 30 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
                "filters": ["engine"],
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "WARNING",
                "formatter": formatter_name,
                "filename": str(_LOG_DIR / "error.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
                "filters": ["error"],
            },
            "perf_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": formatter_name,
                "filename": str(_LOG_DIR / "perf.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "filters": ["performance"],
            },
        },
        "filters": {
            "engine": {"()": __name__ + "._EngineFilter"},
            "business": {"()": __name__ + "._BusinessFilter"},
            "performance": {"()": __name__ + "._PerformanceFilter"},
            "error": {"()": __name__ + "._ErrorFilter"},
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "app_file", "engine_file", "error_file", "perf_file"],
        },
        "loggers": {
            # Reduce noise from third-party libraries
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "urllib3": {"level": "WARNING"},
            "openai": {"level": "WARNING"},
            "langchain": {"level": "WARNING"},
            "langchain_openai": {"level": "WARNING"},
            "chromadb": {"level": "WARNING"},
            "uvicorn": {
                "level": "INFO",
                "propagate": False,
                "handlers": ["console", "app_file", "error_file"],
            },
            "uvicorn.access": {
                "level": "INFO",
                "propagate": False,
                "handlers": ["console", "app_file", "error_file"],
            },
            "uvicorn.error": {
                "level": "INFO",
                "propagate": False,
                "handlers": ["console", "app_file", "error_file"],
            },
        },
    }


def setup_logging(level: str = "INFO", json_fmt: bool = True) -> None:
    """Apply a complete logging configuration.

    This replaces any pre-existing handlers (e.g. uvicorn's defaults) so that
    there is exactly one console stream and the file split we want.
    """
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            if hasattr(stream, "reconfigure"):
                cast(Any, stream).reconfigure(encoding="utf-8", errors="replace")

    logging.config.dictConfig(_build_dict_config(level, json_fmt))


# Kept for backwards compatibility; no longer has any effect on the console handler.
_console_toggles: dict[str, bool] = {}


def configure_console(toggles: dict[str, bool] | None) -> None:
    """Backward-compatible no-op.

    The console handler now outputs all records at the configured level.
    Per-logger toggles are deprecated; use the top-level ``level`` instead.
    """
    _console_toggles.clear()
    if toggles:
        _console_toggles.update(toggles)


# ═══════════════════════════════════════════════════════════════
# Performance logs
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
# Business logs
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
        logger.error(f"[llm] {purpose} failed", extra=data)
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
# Tracing decorator
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
    """Extract key fields from node return value."""
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
        out["scene_id"] = result.get("scene", {}).get("id", "")
        out["pcs"] = len(result.get("pcs", {}))
        out["actors"] = len(result.get("actors", {}))
        out["objects"] = len(result.get("scene_objects", []))
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
