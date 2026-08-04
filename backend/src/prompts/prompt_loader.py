"""统一 prompt 加载器——本地 Jinja2 渲染 + variant 文件覆盖。

用于评估和 A/B 测试场景：
- 默认从 backend/src/prompts/ 读取 .jinja 模板渲染
- 支持通过 variant_file 覆盖 human prompt（A/B 测试 variant 版本）
- engine 层不使用本模块，继续直接用 Jinja2 Environment

用法 / Usage:
    loader = PromptLoader(prompts_root=Path("backend/src/prompts"))

    # 默认渲染（baseline）
    messages = loader.render_messages("dm_create", **template_vars)

    # 用 variant 文件渲染（A/B 测试）
    loader = PromptLoader(prompts_root, variant_file=Path("dm_create_v2.jinja"))
    messages = loader.render_messages("dm_create", **template_vars)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# purpose → (system_template_path, human_template_path) 映射
# None 表示该 purpose 无 system prompt
PURPOSE_TEMPLATES: dict[str, tuple[str | None, str]] = {
    "dm_create": ("dm/_dm_system.jinja", "dm/dm_create.jinja"),
    "dm_narrate": ("dm/_dm_system.jinja", "dm/dm_narrate.jinja"),
    "dm_summarize_narrative": (None, "dm/dm_summarize_narrative.jinja"),
    "dm_summarize_scene": (None, "dm/dm_summarize_scene.jinja"),
    "pc_decision": ("decide/_pc_system.jinja", "decide/pc_decide.jinja"),
    "interact": ("interact/_interact_system.jinja", "interact/interact.jinja"),
    "explore": ("explore/_explore_system.jinja", "explore/explore.jinja"),
    "combat": ("combat/_combat_system.jinja", "combat/combat.jinja"),
    "talk": ("talk/_dialogue_system.jinja", "talk/dialogue.jinja"),
    "reflect_pc": ("reflection/_reflect_system.jinja", "reflection/reflect_pc.jinja"),
    "reflect_actor": ("reflection/_reflect_system.jinja", "reflection/reflect_actor.jinja"),
    "object_spawn": ("spawn/_object_spawn_system.jinja", "spawn/object_spawn.jinja"),
    "actor_spawn": ("spawn/_actor_spawn_system.jinja", "spawn/actor_spawn.jinja"),
    "tilemap_interpret": ("tilemap/_interpret_system.jinja", "tilemap/interpret.jinja"),
}


class PromptLoader:
    """本地 Jinja2 prompt 渲染器，支持 variant 文件覆盖。

    Args:
        prompts_root: prompts 目录路径（含 dm/, decide/ 等子目录）
        variant_file: 可选的 variant human prompt 文件路径（绝对路径），
                      覆盖所有 purpose 的 human template（A/B 测试用）
    """

    def __init__(
        self,
        prompts_root: Path,
        variant_file: Path | None = None,
    ):
        self._env = Environment(
            loader=FileSystemLoader(str(prompts_root)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._prompts_root = prompts_root
        self._variant_file = variant_file
        if variant_file and not variant_file.exists():
            raise FileNotFoundError(f"variant_file 不存在: {variant_file}")

    def render_messages(
        self,
        purpose: str,
        **kwargs: Any,
    ) -> list[BaseMessage]:
        """渲染完整消息列表（system + human）。

        Args:
            purpose: prompt 用途（如 dm_create, pc_decision）
            **kwargs: 模板变量（与 .jinja 文件中的 Jinja2 变量一致）

        Returns:
            消息列表（SystemMessage + HumanMessage）
        """
        if purpose not in PURPOSE_TEMPLATES:
            raise ValueError(f"未知 purpose: {purpose}，可用: {list(PURPOSE_TEMPLATES)}")

        system_path, human_path = PURPOSE_TEMPLATES[purpose]
        messages: list[BaseMessage] = []

        if system_path:
            system_str = self._env.get_template(system_path).render(**kwargs)
            messages.append(SystemMessage(content=system_str))

        # variant_file 覆盖 human prompt
        if self._variant_file:
            human_str = self._variant_file.read_text(encoding="utf-8")
            # variant 文件也用 Jinja2 渲染（支持模板变量）
            from jinja2 import Template

            human_str = Template(human_str).render(**kwargs)
        else:
            human_str = self._env.get_template(human_path).render(**kwargs)
        messages.append(HumanMessage(content=human_str))

        return messages

    def render_system(self, purpose: str, **kwargs: Any) -> str:
        """仅渲染 system prompt。"""
        system_path, _ = PURPOSE_TEMPLATES[purpose]
        if not system_path:
            return ""
        return self._env.get_template(system_path).render(**kwargs)

    def render_human(self, purpose: str, **kwargs: Any) -> str:
        """仅渲染 human prompt（受 variant_file 影响）。"""
        _, human_path = PURPOSE_TEMPLATES[purpose]
        if self._variant_file:
            from jinja2 import Template

            human_str = self._variant_file.read_text(encoding="utf-8")
            return Template(human_str).render(**kwargs)
        return self._env.get_template(human_path).render(**kwargs)
