"""LLM 客户端单元测试——mock OpenAI API."""

import asyncio

import pytest

from src.llm.client import LLMClient
from src.llm.guard import validate_or_fallback, validate_field_non_empty
from src.config import LLMModelConfig, ProviderConfig
from src.schemas.llm_output import LLMSceneDirection, LLMDMNarrative


@pytest.fixture
def provider() -> ProviderConfig:
    return ProviderConfig(type="openai", base_url="https://test.local/v1")


@pytest.fixture
def model_cfg() -> LLMModelConfig:
    return LLMModelConfig(
        model="test-model",
        temperature=0.9,
        timeout=5,
        retries=1,
    )


@pytest.fixture
def client(provider, model_cfg) -> LLMClient:
    return LLMClient(provider, model_cfg)


class TestLLMClient:
    def test_construction(self, client):
        assert client.model == "test-model"
        assert client._cfg.temperature == 0.9
        assert client._cfg.retries == 1

    def test_model_cfg_fields(self, model_cfg):
        assert model_cfg.temperature > 0
        assert model_cfg.timeout > 0
        assert model_cfg.retries >= 0


class TestStructureOutputModels:
    def test_llm_scene_direction_defaults(self):
        d = LLMSceneDirection(plot_brief="test")
        assert d.plot_brief == "test"
        assert d.featured_pcs == []
        assert d.featured_actors == []

    def test_llm_scene_direction_full(self):
        d = LLMSceneDirection(
            plot_brief="The party enters the forest.",
            featured_pcs=["alex", "maya"],
            featured_actors=["goblin_scout"],
        )
        assert len(d.featured_pcs) == 2
        assert "alex" in d.featured_pcs

    def test_llm_narrative_defaults(self):
        n = LLMDMNarrative(narrative="test")
        assert n.narrative == "test"

    def test_llm_scene_direction_json_schema(self):
        schema = LLMSceneDirection.model_json_schema()
        assert "plot_brief" in schema["properties"]
        assert "featured_pcs" in schema["properties"]
        assert "featured_actors" in schema["properties"]


class TestGuardrails:
    def test_validate_none_returns_fallback(self):
        fallback = LLMSceneDirection(plot_brief="fallback scene")
        result = validate_or_fallback(None, LLMSceneDirection, fallback)
        assert result is fallback
        assert result.plot_brief == "fallback scene"

    def test_validate_wrong_type_returns_fallback(self):
        fallback = LLMSceneDirection(plot_brief="fallback")
        wrong = LLMDMNarrative(narrative="wrong type")
        result = validate_or_fallback(wrong, LLMSceneDirection, fallback)
        assert result is fallback

    def test_validate_correct_type_passes_through(self):
        fallback = LLMSceneDirection(plot_brief="fallback")
        correct = LLMSceneDirection(plot_brief="correct", featured_pcs=["alex"])
        result = validate_or_fallback(correct, LLMSceneDirection, fallback)
        assert result is correct
        assert result.plot_brief == "correct"

    def test_validate_field_non_empty_all_present(self):
        data = {"plot_brief": "ok", "featured_pcs": ["alex"]}
        missing = validate_field_non_empty(data, ["plot_brief", "featured_pcs"])
        assert missing == []

    def test_validate_field_non_empty_missing(self):
        data = {"plot_brief": ""}
        missing = validate_field_non_empty(data, ["plot_brief", "featured_pcs"])
        assert "plot_brief" in missing
        assert "featured_pcs" in missing
