"""配置加载器——YAML → Pydantic Settings / Configuration loader — YAML to Pydantic Settings."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class ProviderConfig(BaseModel):
    """LLM 提供商配置 / LLM provider configuration."""
    type: str  # "deepseek" | "anthropic"
    base_url: str | None = None


class ProvidersConfig(BaseModel):
    """多提供商配置（主+降级）/ Multi-provider config (primary + fallback)."""
    primary: ProviderConfig
    fallback: ProviderConfig | None = None


class LLMModelConfig(BaseModel):
    """单 LLM 用途的模型配置 / Single LLM purpose model config."""
    model: str                          # 模型名 / Model name
    fallback_model: str | None = None   # 降级模型 / Fallback model
    temperature: float                  # 温度 / Temperature
    timeout: int                        # 超时（秒）/ Timeout in seconds
    retries: int                        # 重试次数 / Retry count


class LLMConfig(BaseModel):
    """完整的 LLM 配置 / Full LLM configuration."""
    providers: ProvidersConfig
    dm_create: LLMModelConfig           # Phase 1: 创造情境（强模型）/ Create situation
    dm_narrate: LLMModelConfig          # Phase 6: 叙事渲染（中模型）/ Narrate
    pc_decision: LLMModelConfig         # PC 深层决策（中模型）/ PC deep decision
    actor_decision: LLMModelConfig      # Actor 浅层决策（快模型）/ Actor shallow decision
    reflection: LLMModelConfig          # 反思洞察（强模型）/ Reflection insight


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

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> Config:
        """从 config.yaml 加载配置 / Load config from config.yaml."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)


def load_config(path: str = "config.yaml") -> Config:
    """加载配置的便捷函数 / Convenience function to load config."""
    return Config.from_yaml(path)
