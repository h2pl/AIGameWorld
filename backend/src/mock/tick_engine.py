"""Mock Tick 引擎 / Mock Tick Engine — 开发模式下生成模拟 tick 数据

替代真实 Orchestrator.run_tick()。
每 tick 生成：叙事文本 + 角色移动 + 事件日志。
"""

import random

# ── 叙事池 / Narrative pool ──
_NARRATIVES = [
    "Kael 环顾四周，村庄的空气中弥漫着铁匠铺的煤烟味和面包的香气。",
    "一阵凉风从北方吹来，Zeph 的斗篷轻轻飘动。他敏锐地注意到集市角落有个可疑的身影。",
    "Elara 闭上双眼，低声祈祷。圣光在她掌心闪烁，她感到神祇的指引就在附近。",
    "Mira 翻开泛黄的法术书，古老的咒文在她指尖流动。她察觉到这片土地下埋藏着某种魔力。",
    "Garret 挥舞着铁锤，金属撞击声在空气中回荡。'这把剑需要更多的火焰！'他喊道。",
    "Borin 挺直腰板在村口巡逻。北方的森林太安静了，这不寻常。",
    "Selia 整理着货架上的药水和卷轴，不时用眼角余光扫视着来往的旅人。",
    "酒馆里传来喧闹的笑声。有人在高谈阔论关于北边沙漠中古墓的传说。",
    "一阵狼嚎从远方传来，所有人都停下了脚步。那是……不止一只。",
    "夕阳将村庄染成金色。铁匠铺的烟囱渐渐停止了冒烟，夜晚即将来临。",
]

# ── 事件池 / Event pool ──
_EVENT_POOL = [
    {"type": "exploration", "description": "{name} 在周围巡逻", "source": "fighter"},
    {"type": "exploration", "description": "{name} 发现了一个有趣的角落", "source": "rogue"},
    {"type": "exploration", "description": "{name} 检查了教会圣坛", "source": "cleric"},
    {"type": "exploration", "description": "{name} 感知到了魔法波动", "source": "wizard"},
    {"type": "dialogue", "description": "{name} 说道：'今天真是个好日子'", "source": "blacksmith"},
    {"type": "dialogue", "description": "{name} 对路人喊道：'小心那边！'", "source": "guard"},
    {
        "type": "dialogue",
        "description": "{name} 热情招呼：'快来瞧瞧新到的货物！'",
        "source": "merchant",
    },
    {"type": "system", "description": "狼嚎声从北边森林传来", "source": "world"},
    {"type": "combat", "description": "{name} 感到一阵不安，握紧了武器", "source": "fighter"},
]

_CHAR_NAMES = {
    "fighter": "Kael",
    "rogue": "Zeph",
    "cleric": "Elara",
    "wizard": "Mira",
    "blacksmith": "Garret",
    "guard": "Borin",
    "merchant": "Selia",
}


class MockTickEngine:
    """Mock tick 生成器 / Generates mock tick data"""

    def __init__(self):
        self._tick = 0
        self._narr_idx = 0
        self._positions: dict[str, dict] = {}

    def generate_tick(self) -> dict:
        """生成下一个 tick 的完整数据 / Generate next tick's full data"""
        self._tick += 1

        # 叙事 / Narrative
        narrative = _NARRATIVES[self._narr_idx % len(_NARRATIVES)]
        self._narr_idx += 1

        # 角色移动 / Character moves (velocity-based, 0-3 tiles per tick)
        char_moves = []
        for cid in _CHAR_NAMES:
            old = self._positions.get(cid, {"x": 6, "y": 6})
            dx = random.choice([-1, 0, 0, 1, 1])  # 偏向原地/小步
            dy = random.choice([-1, 0, 0, 0, 1])
            nx = max(0, min(39, old["x"] + dx))
            ny = max(0, min(39, old["y"] + dy))
            self._positions[cid] = {"x": nx, "y": ny}
            if dx != 0 or dy != 0:
                char_moves.append({"character_id": cid, "x": nx, "y": ny})

        # 事件 / Events (2-4 per tick)
        n_events = random.randint(2, 4)
        events = []
        for _ in range(n_events):
            ev = random.choice(_EVENT_POOL).copy()
            name = _CHAR_NAMES.get(ev["source"], ev["source"])
            ev["description"] = ev["description"].format(name=name)
            events.append(ev)

        return {
            "tick": self._tick,
            "narrative": narrative,
            "character_moves": char_moves,
            "events": events,
            "errors": [],
        }
