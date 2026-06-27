"""Test config loading with multi-provider and observability structure."""

from pathlib import Path

from src.config import load_config

CONFIG_PATH = str(Path(__file__).resolve().parents[3] / "config.yaml")


def test_config_loads_providers():
    """Config should load with primary + fallback providers."""
    config = load_config(CONFIG_PATH)

    assert config.llm.providers.primary.type == "deepseek"
    assert config.llm.providers.fallback is not None
    assert config.llm.providers.fallback.type == "anthropic"


def test_config_has_fallback_models():
    """Each LLM purpose should have a fallback model."""
    config = load_config(CONFIG_PATH)

    assert config.llm.dm_create.model == "deepseek-reasoner"
    assert config.llm.dm_create.fallback_model is not None
    assert "claude" in config.llm.dm_create.fallback_model


def test_config_observability():
    """Observability config should load Langfuse settings."""
    config = load_config(CONFIG_PATH)

    assert config.observability.langfuse.enabled is True
