# World Pack Loader — Studio world-pack 导入层 / Import Studio world-pack into AIGameWorld
"""World Pack Loader 模块.

loader.py:   world-pack YAML → Domain Model → Repository → SQLite + ChromaDB
validator.py: meta.yaml Pydantic schema validation

术语 / Terminology:
  world-template = Studio templates/ 下原始 YAML 蓝图（字段骨架）
  world-pack     = aw-studio generate 输出的实例 YAML 合集
"""

from .loader import WorldLoader
from .validator import PackValidator, validate_pack_relations

__all__ = ["PackValidator", "WorldLoader", "validate_pack_relations"]
