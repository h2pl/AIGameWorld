"""Structured logging configuration.

Best practices aligned with observability standards:
- Single, complete configuration via dictConfig.
- One console handler: stdout, unfiltered, development-friendly.
- Rotating file handlers split by subsystem:
  - app.log     → API, orchestrator, graph, services, repositories, storage
  - engine.log  → LLM calls and game engines (dm, talk, explore, interact, combat, decision)
  - error.log   → ERROR level from any source
  - perf.log    → performance / latency traces
- Production-grade directory layout: logs/YYYY-MM-DD/<subsystem>.log,
  with time-sliced archives like app.YYYY-MM-DD_HH.log.
- JSON format for production; plain text format for development.
- All third-party noise suppressed.
"""

import contextlib
import functools
import logging
import logging.config
import logging.handlers
import sys
import time as _time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pythonjsonlogger.json import JsonFormatter

from src.config import RotationConfig

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


class _StructuredTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """按日期分目录、按时间切片的文件日志处理器。

    文件布局 / Layout:
      logs/YYYY-MM-DD/<base>.log                (当前活动文件 / active file)
      logs/YYYY-MM-DD/<base>.YYYY-MM-DD_HH.log  (轮转归档 / rotated archive)
    """

    def __init__(
        self,
        base_name: str,
        log_dir: Path,
        when: str = "H",
        interval: int = 1,
        utc: bool = True,
        backup_count: int = 0,
        **kwargs,
    ):
        self._base_name = base_name
        self._log_dir = log_dir
        self._utc = utc
        self._tz = UTC if utc else None
        self._backup_count = backup_count
        path = self._active_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(
            path, when=when, interval=interval, utc=utc, backupCount=backup_count, **kwargs
        )

    def _active_path(self) -> Path:
        now = datetime.now(self._tz)
        return self._log_dir / now.strftime("%Y-%m-%d") / f"{self._base_name}.log"

    def _archive_path(self, t: float) -> Path:
        when = datetime.fromtimestamp(t, tz=self._tz)
        # self.suffix 由父类根据 when 生成，例如 H -> .%Y-%m-%d_%H
        suffix = when.strftime(self.suffix.lstrip("."))
        return self._log_dir / when.strftime("%Y-%m-%d") / f"{self._base_name}.{suffix}.log"

    def rotation_filename(self, default_name: str) -> str:
        # 忽略默认后缀，按结构化路径归档 / Ignore default suffix, use structured path
        t = self.rolloverAt - self.interval
        return str(self._archive_path(t))

    def doRollover(self) -> None:
        # 先按标准逻辑归档并重开当前路径 / Standard archive + reopen at current path
        super().doRollover()

        # 如果跨日期，把新开的空文件移到当前日期目录 / Move to current date dir if day changed
        new_path = self._active_path()
        new_path.parent.mkdir(parents=True, exist_ok=True)
        if new_path != Path(self.baseFilename):
            if self.stream:
                self.stream.close()
                self.stream = None
            old_path = Path(self.baseFilename)
            if old_path.exists():
                if new_path.exists():
                    with old_path.open("rb") as src, new_path.open("ab") as dst:
                        dst.write(src.read())
                    old_path.unlink()
                else:
                    old_path.rename(new_path)
            self.baseFilename = str(new_path)
            self.stream = self._open()


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════


def _build_dict_config(level: str, json_fmt: bool, rotation: RotationConfig) -> dict[str, Any]:
    """Build a complete dictConfig for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    formatter_name = "json" if json_fmt else "human"
    handler_kwargs = {
        "level": "DEBUG",
        "formatter": formatter_name,
        "log_dir": _LOG_DIR,
        "when": rotation.when,
        "interval": rotation.interval,
        "utc": rotation.utc,
        "backup_count": rotation.backup_count,
        "encoding": "utf-8",
    }

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
                "()": "src.utils.logging._StructuredTimedRotatingFileHandler",
                "base_name": "app",
                "filters": ["business"],
                **handler_kwargs,
            },
            "engine_file": {
                "()": "src.utils.logging._StructuredTimedRotatingFileHandler",
                "base_name": "engine",
                "filters": ["engine"],
                **handler_kwargs,
            },
            "error_file": {
                "()": "src.utils.logging._StructuredTimedRotatingFileHandler",
                "base_name": "error",
                "level": "WARNING",
                "filters": ["error"],
                **handler_kwargs,
            },
            "perf_file": {
                "()": "src.utils.logging._StructuredTimedRotatingFileHandler",
                "base_name": "perf",
                "filters": ["performance"],
                **handler_kwargs,
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


def setup_logging(
    level: str = "INFO",
    json_fmt: bool = True,
    rotation: RotationConfig | None = None,
) -> None:
    """Apply a complete logging configuration.

    This replaces any pre-existing handlers (e.g. uvicorn's defaults) so that
    there is exactly one console stream and the file split we want.
    """
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            if hasattr(stream, "reconfigure"):
                cast(Any, stream).reconfigure(encoding="utf-8", errors="replace")

    if rotation is None:
        rotation = RotationConfig()

    logging.config.dictConfig(_build_dict_config(level, json_fmt, rotation))


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
        scene = result.get("scene")
        out["scene_id"] = getattr(scene, "id", "") if scene else ""
        out["pcs"] = len(result.get("pcs", {}))
        out["actors"] = len(result.get("actors", {}))
        out["objects"] = len(result.get("scene_objects", []))
    elif name in ("pc.decide",):
        decs = result.get("pc_decisions", [])
        out["decisions"] = len(decs)
        out["actions"] = [
            getattr(d, "type", None) or (d.get("type") if isinstance(d, dict) else None)
            for d in decs[:5]
        ]
    elif name in ("pc.act",):
        acts = result.get("actions", [])
        out["actions"] = len(acts)
        out["types"] = [
            getattr(a, "action_type", None)
            or (a.get("action_type") if isinstance(a, dict) else None)
            for a in acts[:5]
        ]
    elif name in ("dm.narrate",):
        narrative = result.get("narrative", "")
        if isinstance(narrative, str):
            out["narrative_len"] = len(narrative)
    return out
