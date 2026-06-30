"""World-pack 文件读取 / World-pack file reading.

从 Studio 生成的 world-pack 目录读取 YAML 文件为 dict。
"""

from pathlib import Path

import yaml


def read_pack(pack_dir: Path) -> dict:
    """读取 world-pack 目录下所有实例 YAML → 统一 dict 结构。

    Returns:
        {
            "meta": {},
            "lore": [],
            "scenes": [],
            "player_characters": [],
            "actors": [],
            "items": [],
            "scene_objects": [],
            "story_setup": {"arcs": [], "hooks": []},
        }
    """
    result: dict = {
        "meta": {},
        "lore": [],
        "scenes": [],
        "player_characters": [],
        "actors": [],
        "items": [],
        "scene_objects": [],
        "story_setup": {"arcs": [], "hooks": []},
    }
    if not pack_dir.exists():
        return result

    _read_single(pack_dir / "meta.yaml", result, "meta")
    _read_dir(pack_dir / "lore", result, "lore")
    _read_dir(pack_dir / "scenes", result, "scenes")
    _read_dir(pack_dir / "player_characters", result, "player_characters")
    _read_dir(pack_dir / "actors", result, "actors")
    _read_dir(pack_dir / "items", result, "items")
    _read_dir(pack_dir / "scene_objects", result, "scene_objects")
    _read_single(pack_dir / "story_setup.yaml", result, "story_setup")

    return result


def _read_single(filepath: Path, result: dict, key: str) -> None:
    """读取单个 YAML 文件到 result[key]."""
    if filepath.exists():
        data = yaml.safe_load(filepath.read_text(encoding="utf-8")) or {}
        result[key] = data


def _read_dir(dirpath: Path, result: dict, key: str) -> None:
    """读取目录下所有 .yaml 文件，内容展平加入 result[key]."""
    if not dirpath.exists():
        return
    for yf in sorted(dirpath.glob("*.yaml")):
        data = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        # Unwrap top-level YAML list (e.g., pc/actor files starting with "- id:")
        if isinstance(data, list):
            result[key].extend(data)
        # Unwrap single-key dict with list value (e.g., "items:", "objects:" wrappers)
        elif isinstance(data, dict) and len(data) == 1:
            ((_, wv),) = data.items()
            if isinstance(wv, list):
                result[key].extend(wv)
            else:
                result[key].append(data)
        else:
            result[key].append(data)
