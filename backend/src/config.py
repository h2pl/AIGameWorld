"""配置加载器——YAML → Pydantic Settings / Configuration loader — YAML to Pydantic Settings."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# 自动加载项目根目录 .env
load_dotenv(Path(__file__).parent.parent.parent / ".env")


class ProviderConfig(BaseModel):
    """LLM 提供商配置 / LLM provider configuration."""

    type: str  # "deepseek" | "anthropic" | "openai"
    base_url: str | None = None
    api_key_env: str = "DEEPSEEK_API_KEY"  # 从哪个环境变量读取 API key


class ProvidersConfig(BaseModel):
    """多提供商配置（主+降级）/ Multi-provider config (primary + fallback)."""

    primary: ProviderConfig
    fallback: ProviderConfig | None = None


class LLMModelConfig(BaseModel):
    """单 LLM 用途的模型配置 / Single LLM purpose model config."""

    model: str  # 模型名 / Model name
    base_url: str | None = None  # 覆盖 provider base_url（ZenProxy/GLM等）/ Override base_url
    client_backend: str = (
        "langchain"  # 客户端后端：langchain(ChatOpenAI) | requests(RequestsChatModel)
    )
    fallback_model: str | None = None  # 降级模型 / Fallback model
    temperature: float  # 温度 / Temperature
    timeout: int  # 超时（秒）/ Timeout in seconds
    retries: int  # 重试次数 / Retry count


class LLMConfig(BaseModel):
    """完整的 LLM 配置 / Full LLM configuration."""

    providers: ProvidersConfig
    dm_create: LLMModelConfig  # Phase 1: 创造情境（强模型）/ Create situation
    dm_narrate: LLMModelConfig  # Phase 6: 叙事渲染（中模型）/ Narrate
    pc_decision: LLMModelConfig  # PC 深层决策（中模型）/ PC deep decision
    actor_decision: LLMModelConfig  # Actor 浅层决策（快模型）/ Actor shallow decision
    reflection: LLMModelConfig  # 反思洞察（强模型）/ Reflection insight


class DatabaseConfig(BaseModel):
    """数据库配置 / Database configuration."""

    sqlite_path: str = "data/world.db"
    chroma_path: str = "data/chroma/"


class ServerConfig(BaseModel):
    """服务器配置 / Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000


class WorldConfig(BaseModel):
    """世界配置 / World configuration."""

    default_pack: str = "forgotten_realms"  # 默认加载的 Pack


class AutoRunConfig(BaseModel):
    """自动运行配置 / Auto-run configuration."""

    default_interval: int = 2000  # 毫秒 / milliseconds
    reflection_interval: int = 5  # 每 N ticks 触发一次反思


class LangfuseConfig(BaseModel):
    """Langfuse 可观测性配置 / Langfuse observability config."""

    enabled: bool = False
    tracing_environment: str = "development"


class ObservabilityConfig(BaseModel):
    """可观测性配置 / Observability configuration."""

    langfuse: LangfuseConfig = LangfuseConfig()


class Config(BaseSettings):
    """全局配置根 / Global config root."""

    server: ServerConfig = ServerConfig()
    world: WorldConfig = WorldConfig()
    llm: LLMConfig
    database: DatabaseConfig = DatabaseConfig()
    auto_run: AutoRunConfig = AutoRunConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    mock_mode: bool = True  # dev 默认 mock / default to mock in dev

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> Config:
        """从 config.yaml 加载配置，provider + purposes 分离合并."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 选择 provider（环境变量 LLM_PROVIDER > yaml llm_provider）
        providers = data.pop("llm_providers", None)
        purposes = data.pop("llm_purposes", None)
        yaml_provider = data.pop("llm_provider", None)
        if providers and purposes:
            provider_name = os.environ.get("LLM_PROVIDER") or yaml_provider
            if not provider_name or provider_name not in providers:
                available = ", ".join(providers.keys())
                raise ValueError(
                    f"LLM provider '{provider_name}' not found. Available: {available}"
                )
            provider = providers[provider_name]
            backend = provider.pop("client_backend", "langchain")
            default_model = provider.pop("model", None)
            # 组装 llm：provider 的 client_backend + model 注入每个 purpose
            merged = {}
            for name, pur in purposes.items():
                merged[name] = {**pur, "client_backend": backend}
                if default_model and "model" not in pur:
                    merged[name]["model"] = default_model
            data["llm"] = {
                "providers": {"primary": {"type": "openai", **provider}},
                **merged,
            }
            print(f"[Config] LLM provider: {provider_name}")
        return cls(**data)


def load_config(path: str = "config.yaml") -> Config:
    """加载配置的便捷函数 / Convenience function to load config."""
    return Config.from_yaml(path)
