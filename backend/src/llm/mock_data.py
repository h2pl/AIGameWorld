"""Mock 数据集——合理且可用于前端展示的默认 LLM 响应 / Realistic mock responses for frontend display.

每个数据集 (dataset) 对应一个"故事线"，包含所有 purpose 的完整 mock 数据。
通过 config 或 LLMClient 的 mock_dataset 参数切换。
"""

# ═══════════════════════════════════════════════════════════════
# 数据集类型定义 / Dataset type definition
# ═══════════════════════════════════════════════════════════════
MockDataset = dict[str, dict]


# ═══════════════════════════════════════════════════════════════
# 数据集 1：酒馆线 / Tavern storyline
# ═══════════════════════════════════════════════════════════════
DATASET_TAVERN: MockDataset = {
    "dm_create": {
        "hints": [
            "吧台后的木桶堆得很高，似乎藏着什么。",
            "角落里有个披斗篷的人，一直盯着门口看。",
            "空气中弥漫着麦酒和烤肉的香味，偶尔传来几声粗犷的笑声。",
        ],
        "plot_brief": "冒险者们踏入酒馆，等待他们的可能是一场蓄谋已久的相遇。",
        "scene_id": "tavern",
    },
    "dm_narrate": {
        "narrative": "推开厚重的橡木门，暖黄色的烛光洒在冒险者们身上。酒馆里比往常安静，几个常客低头啜饮，似乎都在刻意避开彼此的目光。吧台后面，老板娘 Greta 擦拭着一只锡杯，朝新来的客人们点了点头——那眼神好像在说：「你们来得正是时候。」",
    },
    "pc_decision": {
        "action_type": "talk",
        "target_id": "innkeeper",
        "target_type": "actor",
        "reasoning": "Greta 的眼神暗示她有话要说，先打听一下最近镇上有什么异常。",
    },
    "actor_decision": {
        "action_type": "talk",
        "target_id": "alex",
        "target_type": "pc",
        "reasoning": "这些冒险者装备精良，生意来了。DM 让我留意打听商队消息的人。",
    },
    "talk": {
        "turns": [
            {"speaker_id": "alex", "text": "晚上好，Greta。今天酒馆怎么这么安静？"},
            {
                "speaker_id": "innkeeper",
                "text": "唉，别提了。最近商队都不敢走夜路，说北边的林子里有东西。",
            },
            {"speaker_id": "alex", "text": "什么东西？"},
            {
                "speaker_id": "innkeeper",
                "text": "没人活着回来说清楚。但你要是感兴趣……镇上公告栏贴着悬赏。",
            },
        ],
    },
    "reflection": {
        "behavior_summary": "从 Greta 处获得了关于北方森林的线索，决定去查看公告栏。",
        "insight": "这个小镇暗藏危机——商队消失不是偶然。",
    },
    "summarize": {
        "summary": "冒险者抵达酒馆，从老板娘 Greta 口中得知北方森林有危险，镇上悬赏调查。",
    },
}

# ═══════════════════════════════════════════════════════════════
# 数据集 2：战斗线 / Combat storyline
# ═══════════════════════════════════════════════════════════════
DATASET_COMBAT: MockDataset = {
    "dm_create": {
        "hints": [
            "灌木丛在无风的情况下摇晃了几下。",
            "地面上有明显的拖拽痕迹，通向林子深处。",
            "空气中有淡淡的血腥味。",
        ],
        "plot_brief": "冒险者们在林间小道上遭遇了伏击——一群地精从灌木丛后冲了出来。",
        "scene_id": "forest_path",
    },
    "dm_narrate": {
        "narrative": "刚走到林中小路的拐弯处，一阵刺耳的尖啸打破了寂静。三个绿皮地精从灌木丛后跳了出来，挥舞着生锈的短剑和木棒，龇牙咧嘴地朝冒险者们冲来。他们的眼睛里闪着贪婪的光——看来是把这几个旅人当成了今天的猎物。",
    },
    "pc_decision": {
        "action_type": "combat",
        "target_id": "goblin_scout",
        "target_type": "actor",
        "reasoning": "敌人已经发起攻击，必须立刻迎战。先解决最前面的侦察兵。",
    },
    "actor_decision": {
        "action_type": "combat",
        "target_id": "alex",
        "target_type": "pc",
        "reasoning": "这些人类闯进了地精的领地，必须赶走他们！",
    },
    "talk": {
        "turns": [
            {"speaker_id": "goblin_scout", "text": "呱啊！人类！交出金币！"},
            {"speaker_id": "alex", "text": "想得美，小怪物。拔剑吧！"},
        ],
    },
    "reflection": {
        "behavior_summary": "在森林小径遭遇地精伏击，展开了战斗。",
        "insight": "这片森林可能被地精部落控制了，需要小心后续的埋伏。",
    },
    "summarize": {
        "summary": "冒险者在森林小径遭遇地精伏击，展开战斗。",
    },
}

# ═══════════════════════════════════════════════════════════════
# 数据集注册 / Dataset registry
# ═══════════════════════════════════════════════════════════════
DATASETS: dict[str, MockDataset] = {
    "tavern": DATASET_TAVERN,
    "combat": DATASET_COMBAT,
}

# 默认数据集 / Default dataset
DEFAULT_DATASET = "tavern"


# ═══════════════════════════════════════════════════════════════
# 查询接口 / Query interface
# ═══════════════════════════════════════════════════════════════
def get_dataset(name: str = "") -> MockDataset:
    """获取指定 mock 数据集 / Get a specific mock dataset."""
    return DATASETS.get(name, DATASETS[DEFAULT_DATASET])


def get_mock(purpose: str, dataset_name: str = "") -> dict:
    """获取某个 purpose 的 mock 数据 / Get mock data for a specific purpose."""
    ds = get_dataset(dataset_name)
    return ds.get(purpose, {})
