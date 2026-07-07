"""Tests for structured logging configuration."""

import json
import logging
import sys
from contextlib import suppress

import pytest

from src.utils.logging import get_logger, setup_logging


class TestSetupLogging:
    """验证日志配置正确性 / Verify logging setup correctness."""

    @pytest.fixture(autouse=True)
    def reset_logging(self, monkeypatch, tmp_path):
        """每个用例前重置 logging，并指向临时日志目录."""
        monkeypatch.setattr("src.utils.logging._LOG_DIR", tmp_path)
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)
            with suppress(Exception):
                h.close()
        root.setLevel(logging.NOTSET)
        for name in list(logging.Logger.manager.loggerDict):
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)
            logger.propagate = True

    def test_console_handler_is_single(self):
        """应只有 1 个控制台 handler（stdout），避免重复输出."""
        setup_logging("INFO")
        handlers = [
            h
            for h in logging.getLogger().handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert len(handlers) == 1
        assert handlers[0].stream is sys.stdout

    def test_file_handlers_split_by_subsystem(self, tmp_path):
        """文件日志按子系统分流."""
        setup_logging("INFO")

        get_logger("api").info("api log")
        get_logger("llm").info("llm log")
        get_logger("engine.dm").info("engine log")
        get_logger("performance").info("perf log")
        get_logger("service").error("service error")

        # 强制关闭所有文件 handler，确保缓冲写入
        for h in logging.getLogger().handlers:
            if hasattr(h, "flush"):
                h.flush()
            if hasattr(h, "close"):
                h.close()

        app_log = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("app.log*"))
        engine_log = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("engine.log*"))
        error_log = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("error.log*"))
        perf_log = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("perf.log*"))

        # app.log: 业务日志，不含 engine/llm/perf
        assert "api log" in app_log
        assert "service error" in app_log
        assert "llm log" not in app_log
        assert "engine log" not in app_log
        assert "perf log" not in app_log

        # engine.log: engine + llm
        assert "llm log" in engine_log
        assert "engine log" in engine_log
        assert "api log" not in engine_log

        # error.log: 所有 ERROR+
        assert "service error" in error_log

        # perf.log: performance only
        assert "perf log" in perf_log
        assert "api log" not in perf_log

    def test_json_format(self, tmp_path):
        """默认 JSON 格式输出."""
        setup_logging("INFO", json_fmt=True)
        get_logger("api").info("hello")
        for h in logging.getLogger().handlers:
            if hasattr(h, "flush"):
                h.flush()
            if hasattr(h, "close"):
                h.close()

        app_log = (tmp_path / "app.log").read_text(encoding="utf-8")
        record = json.loads(app_log.strip().splitlines()[0])
        assert record["name"] == "api"
        assert record["message"] == "hello"

    def test_plain_text_format(self, tmp_path):
        """可切换为纯文本格式."""
        setup_logging("INFO", json_fmt=False)
        get_logger("api").info("hello")
        for h in logging.getLogger().handlers:
            if hasattr(h, "flush"):
                h.flush()
            if hasattr(h, "close"):
                h.close()

        app_log = (tmp_path / "app.log").read_text(encoding="utf-8")
        assert "api" in app_log
        assert "hello" in app_log
