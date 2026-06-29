"""结构化日志辅助 / Structured logging helpers.

按 common-observability skill: 用 extra= 传结构化数据。
Windows 下通过 setup_logging() 强制 stdout/stderr 为 UTF-8。
"""

import contextlib
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """初始化日志 / Initialize logging with UTF-8 encoding on Windows."""
    # Windows sys.stdout 默认 cp936(GBK)，logging 中文全乱码，强制 UTF-8
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")  # pyright: ignore[reportAttributeAccessIssue]

    # 只配置 root handler，避免重复
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        h = logging.StreamHandler(sys.stderr)
        h.setLevel(level)
        h.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(name)-24s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        ))
        root.addHandler(h)

    # 降噪——第三方库日志只显示 WARNING+
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3", "openai", "langchain", "langchain_openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log_phase(phase: str, tick: int, elapsed: float | None = None, **extra) -> None:
    """记录 Graph Phase 执行 / Log Graph phase execution."""
    data = {"phase": phase, "tick": tick, **extra}
    if elapsed is not None:
        data["elapsed_ms"] = round(elapsed * 1000, 1)
    logging.getLogger("phase").info(f"[{phase}] tick={tick}", extra=data)


def log_llm(purpose: str, action: str, elapsed: float, extra: dict | None = None) -> None:
    """记录 LLM 调用 / Log LLM call."""
    data = {"purpose": purpose, "action": action, "elapsed_ms": round(elapsed * 1000, 1)}
    if extra:
        data.update(extra)
    logger = logging.getLogger("llm")
    if action == "error":
        logger.error(f"[{purpose}] 失败 / failed", extra=data)
    else:
        logger.info(f"[{purpose}] ok", extra=data)
