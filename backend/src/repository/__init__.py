"""Repository 层：领域数据访问（只操作领域实体，不暴露 dict/ORM）."""

from .world_state_repo import CharacterRepo
from .sqlite_world_state_repo import SQLiteCharacterRepo

__all__ = ["CharacterRepo", "SQLiteCharacterRepo"]
