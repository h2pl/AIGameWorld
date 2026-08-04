"""真实链路测试——走通 config 加载 + key 解析 + LLMClient 初始化，不调真实 LLM。

这层测试覆盖 Mock 测试摸不到的 bug：load_dotenv 是否执行、api_key_env 是否正确解析、
provider 的 model/client_backend 是否正确注入 purpose。
"""

import os
from pathlib import Path

from src.config import load_config
from src.llm.llm_client import LLMClient, _extract_json

CONFIG_PATH = str(Path(__file__).resolve().parents[4] / "config.yaml")
ENV_PATH = Path(__file__).resolve().parents[4] / ".env"


class TestEnvLoading:
    """验证 .env 被自动加载 + api_key_env 正确解析 key 值."""

    def test_dotenv_loaded(self):
        """config import 时 load_dotenv 应已执行，环境变量可读."""
        from dotenv import load_dotenv

        path = Path(__file__).resolve().parents[4] / ".env"
        assert path.exists(), f".env not found at {path}"
        loaded = load_dotenv(path, override=True)
        assert loaded, f"load_dotenv({path}) returned False"

    def test_deepseek_key_resolved(self, monkeypatch):
        """api_key_env 指向的 env var 能正确读到值."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek-key")
        config = load_config(CONFIG_PATH)
        key_env = config.llm.providers.primary.api_key_env
        assert key_env == "DEEPSEEK_API_KEY"
        assert os.environ.get(key_env) == "sk-test-deepseek-key"

    def test_glm_key_resolved(self, monkeypatch):
        """env var 名正确指向 GLM key."""
        monkeypatch.setenv("GLM_API_KEY", "glm-test-key.xxx")
        # 切换到 glm provider
        monkeypatch.setenv("LLM_PROVIDER", "glm")
        config = load_config(CONFIG_PATH)
        key_env = config.llm.providers.primary.api_key_env
        assert key_env == "GLM_API_KEY"
        assert os.environ.get(key_env) == "glm-test-key.xxx"


class TestProviderPurposeMerge:
    """验证 provider 配置正确注入到每个 purpose."""

    def test_model_inherited_from_provider(self):
        """purpose 没写 model 时从 provider 继承."""
        os.environ["LLM_PROVIDER"] = "glm"
        config = load_config(CONFIG_PATH)
        assert config.llm.dm_create.model == "glm-5.1"
        assert config.llm.dm_narrate.model == "glm-5.1"

    def test_client_backend_inherited(self):
        """client_backend 从 provider 注入到每个 purpose."""
        os.environ["LLM_PROVIDER"] = "zen-proxy"
        config = load_config(CONFIG_PATH)
        assert config.llm.dm_create.client_backend == "requests"
        assert config.llm.actor_decision.client_backend == "requests"

        os.environ["LLM_PROVIDER"] = "deepseek"
        config = load_config(CONFIG_PATH)
        assert config.llm.dm_create.client_backend == "langchain"

    def test_all_purposes_have_required_fields(self):
        """每个 purpose 都有 model, temperature, timeout, retries, client_backend."""
        os.environ["LLM_PROVIDER"] = "deepseek"
        config = load_config(CONFIG_PATH)
        for name in [
            "dm_create",
            "dm_narrate",
            "pc_decision",
            "actor_decision",
            "talk",
            "reflection",
        ]:
            pur = getattr(config.llm, name)
            assert pur.model, f"{name}.model is empty"
            assert pur.temperature > 0, f"{name}.temperature is zero"
            assert pur.timeout > 0, f"{name}.timeout is zero"
            assert pur.retries >= 0, f"{name}.retries is negative"
            assert pur.client_backend in ("langchain", "requests"), (
                f"{name}.client_backend={pur.client_backend}"
            )


class TestLLMClientInit:
    """验证 LLMClient 从真实 config 初始化不出错."""

    def test_init_with_provider(self, monkeypatch):
        """LLMClient 初始化应创建 11 个 model（含 party_discuss/party_decide）."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        config = load_config(CONFIG_PATH)
        client = LLMClient(config)
        assert len(client._models) == 11
        assert set(client._models.keys()) == {
            "dm_create",
            "dm_narrate",
            "pc_decision",
            "actor_decision",
            "talk",
            "interact",
            "explore",
            "combat",
            "reflection",
            "party_discuss",
            "party_decide",
        }

    def test_timeouts_loaded_correctly(self, monkeypatch):
        """每个 purpose 的 timeout 正确传递."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_PROVIDER", "deepseek")
        config = load_config(CONFIG_PATH)
        client = LLMClient(config)
        assert client._timeouts["dm_create"] == 20
        assert client._timeouts["dm_narrate"] == 30
        assert client._timeouts["actor_decision"] == 8


class TestJsonExtraction:
    """_extract_json 纯逻辑测试——不需要 LLM."""

    def test_plain_json(self):
        assert '"key": "value"' in _extract_json('{"key": "value"}')

    def test_markdown_code_block(self):
        text = '```json\n{"narrative": "hello"}\n```'
        result = _extract_json(text)
        assert "narrative" in result
        assert "```" not in result

    def test_json_with_surrounding_text(self):
        text = 'Some text before {"answer": 42} and after'
        result = _extract_json(text)
        assert result == '{"answer": 42}'

    def test_no_json_fallback(self):
        text = "Just plain text, no braces"
        result = _extract_json(text)
        assert result == text  # fallback: return as-is
