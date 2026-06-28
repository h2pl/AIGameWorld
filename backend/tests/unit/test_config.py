"""Test config loading with OpenAI-compatible providers."""

from pathlib import Path

from src.config import load_config

CONFIG_PATH = str(Path(__file__).resolve().parents[3] / "config.yaml")


def test_config_loads_providers():
    """Config should load primary provider."""
    config = load_config(CONFIG_PATH)
    assert config.llm.providers.primary.type == "openai"
    assert config.llm.providers.primary.base_url is not None


def test_config_model_configs_complete():
    """Each LLM purpose should have model configured."""
    config = load_config(CONFIG_PATH)
    assert config.llm.dm_create.model == "deepseek-v4-flash-free"
    assert config.llm.dm_create.temperature == 0.9
    assert config.llm.dm_narrate.model == "deepseek-v4-flash-free"
    assert config.llm.pc_decision.timeout == 10
    assert config.llm.actor_decision.retries == 1
    assert config.llm.reflection.temperature == 0.5


def test_model_can_override_base_url():
    """LLMModelConfig.base_url defaults to None (use provider)."""
    config = load_config(CONFIG_PATH)
    assert config.llm.dm_create.base_url is None

    from src.config import LLMModelConfig
    cfg = LLMModelConfig(model="glm-4-plus", temperature=0.7, timeout=10, retries=1,
                         base_url="https://open.bigmodel.cn/api/paas/v4")
    assert cfg.base_url == "https://open.bigmodel.cn/api/paas/v4"


def test_config_observability():
    """Observability config should load Langfuse settings."""
    config = load_config(CONFIG_PATH)
    assert config.observability.langfuse.enabled is True
