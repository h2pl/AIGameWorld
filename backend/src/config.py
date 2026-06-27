"""Configuration loader - YAML to Pydantic Settings."""

from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class LLMModelConfig(BaseModel):
    model: str
    temperature: float
    timeout: int
    retries: int


class LLMConfig(BaseModel):
    dm_create: LLMModelConfig
    dm_narrate: LLMModelConfig
    pc_decision: LLMModelConfig
    actor_decision: LLMModelConfig
    reflection: LLMModelConfig


class DatabaseConfig(BaseModel):
    sqlite_path: str = "data/world.db"
    chroma_path: str = "data/chroma/"


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class WorldConfig(BaseModel):
    default_pack: str = "forgotten_realms"


class AutoRunConfig(BaseModel):
    default_interval: int = 2000


class Config(BaseSettings):
    server: ServerConfig = ServerConfig()
    world: WorldConfig = WorldConfig()
    llm: LLMConfig
    database: DatabaseConfig = DatabaseConfig()
    auto_run: AutoRunConfig = AutoRunConfig()

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Config":
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)


def load_config(path: str = "config.yaml") -> Config:
    return Config.from_yaml(path)
