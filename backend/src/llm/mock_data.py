"""Mock 数据集——多示例随机抽取 / Multiple examples per event type, selected randomly.

每种事件有 3~5 个示例，每次调用 get_mock() 随机返回一个。
pc_decision 使用轮转池，保证覆盖 talk/explore/interact 全部动作类型。
"""

import random

MockDataset = dict[str, list[dict]]


# ═══════════════════════════════════════════════════════════════
# PC 决策轮转池 / PC decision rotation pool
# ═══════════════════════════════════════════════════════════════
_PC_DECISIONS: list[dict] = [
    {
        "action_type": "talk",
        "target_id": "merchant",
        "target_type": "actor",
        "reasoning": "Greta 的眼神暗示她有话要说，先打听一下最近镇上有什么异常。",
    },
    {
        "action_type": "explore",
        "target_id": None,
        "target_type": None,
        "reasoning": "也许应该在酒馆周围四处看看，说不定能发现什么线索。",
    },
    {
        "action_type": "talk",
        "target_id": "blacksmith",
        "target_type": "actor",
        "reasoning": "铁匠看起来是个有故事的人，去和他聊聊也许能打听到什么。",
    },
    {
        "action_type": "interact",
        "target_id": "chest_1",
        "target_type": "scene_object",
        "reasoning": "角落里那个箱子看起来有点可疑，让我检查一下里面有什么。",
    },
    {
        "action_type": "explore",
        "target_id": None,
        "target_type": None,
        "reasoning": "这个酒馆的布局让人在意，到处巡视一下看看有没有暗门或隐藏的线索。",
    },
    {
        "action_type": "talk",
        "target_id": "guard",
        "target_type": "actor",
        "reasoning": "门口的守卫似乎欲言又止，去和他打探一下消息。",
    },
    {
        "action_type": "explore",
        "target_id": None,
        "target_type": None,
        "reasoning": "外面的街道上似乎有什么动静，出去查看一下。",
    },
    {
        "action_type": "interact",
        "target_id": "door_cellar",
        "target_type": "scene_object",
        "reasoning": "那个通往地窖的门虚掩着，说不定下面有什么好东西。",
    },
    {
        "action_type": "talk",
        "target_id": "merchant",
        "target_type": "actor",
        "reasoning": "想问问老板娘关于北边森林的更多细节。",
    },
    {
        "action_type": "explore",
        "target_id": None,
        "target_type": None,
        "reasoning": "沙漠中的遗迹似乎有秘密通道，必须仔细搜索。",
    },
    {
        "action_type": "talk",
        "target_id": "guard",
        "target_type": "actor",
        "reasoning": "守卫看起来知道沙漠里的危险，向他打听一下注意事项。",
    },
    {
        "action_type": "interact",
        "target_id": "chest_wooden",
        "target_type": "scene_object",
        "reasoning": "角落里有个古旧的木箱，上面雕刻着奇怪的符文。",
    },
    {
        "action_type": "combat",
        "target_id": "goblin",
        "target_type": "actor",
        "reasoning": "那只地精虎视眈眈，必须先下手为强。",
    },
    {
        "action_type": "combat",
        "target_id": "skeleton",
        "target_type": "actor",
        "reasoning": "不死生物不能放任它在村子里游荡。",
    },
    {
        "action_type": "combat",
        "target_id": "orc_boss",
        "target_type": "actor",
        "reasoning": "首领才是威胁的根源，集中火力解决它。",
    },
]


def _normalize_action(action: dict) -> dict:
    """补全 PC decision 的 thought/reasoning 字段，避免 schema 校验失败."""
    normalized = dict(action)
    if "thought" not in normalized:
        normalized["thought"] = normalized.get("reasoning", "我做出了这个决定。")
    if "reasoning" not in normalized:
        normalized["reasoning"] = normalized.get("thought", "等待时机。")
    return normalized


class _PcDecisionRotator:
    def __init__(self) -> None:
        self._idx = 0

    def next(self) -> dict:
        a1 = _PC_DECISIONS[self._idx % len(_PC_DECISIONS)]
        self._idx += 1
        a2 = _PC_DECISIONS[self._idx % len(_PC_DECISIONS)]
        self._idx += 1
        return {"actions": [_normalize_action(a1), _normalize_action(a2)]}


_pc_rotator = _PcDecisionRotator()


# ═══════════════════════════════════════════════════════════════
# 数据集 1：酒馆线 / Tavern storyline
# ═══════════════════════════════════════════════════════════════
# 包含 dm_create/dm_narrate/talk/reflection 等完整连线
DATASET_TAVERN: MockDataset = {
    "dm_create": [
        {
            "hints": [
                "吧台后的木桶堆得很高，似乎藏着什么。",
                "角落里有个披斗篷的人，一直盯着门口看。",
                "空气中弥漫着麦酒和烤肉的香味，偶尔传来几声粗犷的笑声。",
            ],
            "plot_brief": "冒险者们踏入酒馆，等待他们的可能是一场蓄谋已久的相遇。",
            "scene_id": "village_elderwood",
        },
        {
            "hints": [
                "墙上贴着一张泛黄的悬赏令，赏金高得离谱。",
                "酒馆的壁炉烧得很旺，但角落里却有一股莫名的寒意。",
                "吧台后面，一个独眼老人正在擦玻璃杯，眼神锐利。",
            ],
            "plot_brief": "酒馆里弥漫着不安的气氛，似乎每个人都藏着秘密。",
            "scene_id": "village_elderwood",
        },
        {
            "hints": [
                "一个吟游诗人坐在角落里，弹着忧伤的曲调。",
                "几个冒险者围在一张桌子前，低声讨论着什么地图。",
                "酒馆老板紧张地朝窗外看了一眼。",
            ],
            "plot_brief": "平静的夜晚被一阵马蹄声打破，一个浑身是血的旅人冲了进来。",
            "scene_id": "village_elderwood",
        },
    ],
    "dm_narrate": [
        {
            "narrative": "推开厚重的橡木门，暖黄色的烛光洒在冒险者们身上。酒馆里比往常安静，几个常客低头啜饮，似乎都在刻意避开彼此的目光。吧台后面，老板娘 Greta 擦拭着一只锡杯，朝新来的客人们点了点头——那眼神好像在说：「你们来得正是时候。」",
        },
        {
            "narrative": "火炉噼啪作响，酒馆里弥漫着烤肉和麦酒的香气。角落里坐着几个穿着破烂的旅人，他们压低声音交谈着。一个戴斗篷的陌生人坐在阴影里，像是在等什么人。铁匠靠在吧台边，用粗糙的手指敲着木桌，发出单调的节奏声。",
        },
        {
            "narrative": "酒馆的门被风吹得咯吱作响。地板上散落着稻草，壁炉的火光照亮了墙上褪色的挂毯。这是一个典型的边境小镇酒馆——粗糙、简陋，但莫名其妙地让人感到安心。如果忽略角落里那个一直盯着你的独眼老人的话。",
        },
    ],
    "talk": [
        {
            "turns": [
                {"speaker_id": "cleric", "text": "晚上好，Greta。今天酒馆怎么这么安静？"},
                {
                    "speaker_id": "merchant",
                    "text": "唉，别提了。最近商队都不敢走夜路，说北边的林子里有东西。",
                },
                {"speaker_id": "cleric", "text": "什么东西？"},
                {
                    "speaker_id": "merchant",
                    "text": "没人活着回来说清楚。但你要是感兴趣……镇上公告栏贴着悬赏。",
                },
            ],
        },
        {
            "turns": [
                {"speaker_id": "fighter", "text": "铁匠大叔，你这锤子够沉的啊。"},
                {
                    "speaker_id": "blacksmith",
                    "text": "哈！矮人打造的，传了三代了。你要是有好铁，我也能给你打一把。",
                },
                {"speaker_id": "fighter", "text": "最近有没有什么奇怪的客人来过？"},
                {
                    "speaker_id": "blacksmith",
                    "text": "有。三天前一个伤员来修盔甲，盔甲上有爪痕——不是野兽的爪痕。",
                },
            ],
        },
        {
            "turns": [
                {"speaker_id": "wizard", "text": "守卫先生，北边的森林里真的有怪物吗？"},
                {
                    "speaker_id": "guard",
                    "text": "不是怪物……至少不是普通的怪物。有人说看到过黑影，比树还高。",
                },
                {"speaker_id": "wizard", "text": "有意思。你们有没有派人去调查？"},
                {
                    "speaker_id": "guard",
                    "text": "去了三队，只回来了一个。他现在住在镇上的医馆里，但什么也不肯说。",
                },
            ],
        },
        {
            "turns": [
                {"speaker_id": "rogue", "text": "朋友，你一个人坐在这里喝闷酒，有心事？"},
                {
                    "speaker_id": "merchant",
                    "text": "不是心事，是后悔。我昨天不该把那张地图卖给那个黑袍人。",
                },
                {"speaker_id": "rogue", "text": "什么地图？"},
                {
                    "speaker_id": "merchant",
                    "text": "北边废弃神殿的地图。我本来以为只是废纸，但那黑袍人的眼神……不像是凡人。",
                },
            ],
        },
        {
            "turns": [
                {"speaker_id": "cleric", "text": "Greta，这杯麦酒味道不错，是你自己酿的吗？"},
                {
                    "speaker_id": "merchant",
                    "text": "是镇上的磨坊主酿的。不过说起来，他上周不见了。",
                },
                {"speaker_id": "cleric", "text": "不见了？"},
                {
                    "speaker_id": "merchant",
                    "text": "去了北边的林子采蘑菇，再也没有回来。他老婆天天在镇口等。",
                },
            ],
        },
    ],
    "explore": [
        {
            "end_x": 10,
            "end_y": 12,
            "explore_record": "吧台后方的木地板有一块微微翘起，下面似乎藏着一张泛黄的羊皮纸。",
        },
        {
            "end_x": 8,
            "end_y": 15,
            "explore_record": "酒馆后门的台阶上有一串湿脚印，通向小巷深处，泥里还嵌着一枚银币。",
        },
        {
            "end_x": 12,
            "end_y": 8,
            "explore_record": "窗台上摆着一个积满灰尘的陶罐，罐底隐约可见缕刻的纹路——像是某种古老的徽记。",
        },
    ],
    "interact": [
        {
            "success": True,
            "narration": "他轻轻撬开木箱的锁扣，箱盖发出一声沉闷的吱呀。里面整齐地码放着几卷羊皮纸，墨迹虽已泛黄，但字迹依然清晰。",
        },
        {
            "success": False,
            "narration": "他用力推动地窖门，但门板纹丝不动——铁栓从内侧锁死了，除非找到钥匙或另寻他路。",
        },
        {
            "success": True,
            "narration": "他用匕首挑开箱盖的铜锁，里面露出一枚刻着龙纹的徽章和一小袋金币。",
        },
    ],
    "combat": [
        {
            "narration": "他挥剑劈向地精，剑锋在烛光下划出一道弧光，将敌人逼得连退两步。",
            "target_defeated": False,
            "result": "地精受创但仍站立",
        },
        {
            "narration": "长矛擦过他的护甲，火星四溅；他趁机反手一击，重创了面前的敌人。",
            "target_defeated": False,
            "result": "敌人受创",
        },
        {
            "narration": "他一个侧身躲过挥来的木棒，匕首顺势刺入敌人的软肋，地精发出一声惨叫。",
            "target_defeated": True,
            "result": "地精倒地不起",
        },
    ],
    "actor_decision": [
        {
            "action_type": "talk",
            "target_id": "cleric",
            "target_type": "pc",
            "reasoning": "这些冒险者装备精良，生意来了。DM 让我留意打听商队消息的人。",
        },
        {
            "action_type": "talk",
            "target_id": "fighter",
            "target_type": "pc",
            "reasoning": "终于看到实力不错的冒险者了，得把北边的情况告诉他们。",
        },
        {
            "action_type": "talk",
            "target_id": "rogue",
            "target_type": "pc",
            "reasoning": "那个贼头贼脑的家伙看起来对秘密很感兴趣，正好可以利用他。",
        },
    ],
    "reflection": [
        {
            "behavior_summary": "从 Greta 处获得了关于北方森林的线索，决定去查看公告栏。",
            "insight": "这个小镇暗藏危机——商队消失不是偶然。",
        },
        {
            "behavior_summary": "铁匠透露了三天前的伤员事件，盔甲上的爪痕很可疑。",
            "insight": "北边的威胁可能超出了普通野兽的范畴。",
        },
        {
            "behavior_summary": "收集了多方情报——猎人失踪、商队不敢走夜路、奇怪的黑袍人。",
            "insight": "这些事件之间似乎有某种联系。",
        },
    ],
    "summarize": [
        {"summary": "冒险者抵达酒馆，从老板娘 Greta 口中得知北方森林有危险，镇上悬赏调查。"},
        {"summary": "冒险者与铁匠交谈，得知曾有伤员带着奇怪爪痕回来，此事不简单。"},
        {"summary": "多方打听后，冒险者拼凑出真相：北方废弃神殿有超自然力量，镇上已有数人失踪。"},
    ],
    # ═══════════════════════════════════════════════════════════════
    # tilemap 语义解读 / Dynamic scene entity generation
    # ═══════════════════════════════════════════════════════════════
    "interpret_tilemap": [
        {
            "summary": "边境小镇的街道图：东侧是铁匠铺和酒馆，中央有喷泉广场，西侧是民居和一口古井。镇子被木栅栏围绕，南边是通往森林的出口，北边是通往山区的崎岖小路。"
        },
    ],
    "spawn_actors": [
        {
            "actors": [
                {
                    "id": "actor_blacksmith",
                    "name": "铁匠",
                    "role": "blacksmith",
                    "race": "dwarf",
                    "disposition": "friendly",
                    "position_x": 10,
                    "position_y": 10,
                },
                {
                    "id": "actor_merchant",
                    "name": "旅行商人",
                    "role": "merchant",
                    "race": "human",
                    "disposition": "neutral",
                    "position_x": 12,
                    "position_y": 12,
                },
            ]
        },
    ],
    "spawn_objects": [
        {
            "objects": [
                {
                    "id": "obj_chest",
                    "name": "旧木箱",
                    "object_type": "container",
                    "position_x": 14,
                    "position_y": 14,
                    "interact_data": {"locked": False, "items": ["旧地图"]},
                },
                {
                    "id": "obj_well",
                    "name": "古井",
                    "object_type": "decoration",
                    "position_x": 20,
                    "position_y": 20,
                    "interactable": False,
                },
            ]
        },
    ],
}

# ═══════════════════════════════════════════════════════════════
# 数据集 2：沙漠线 / Desert storyline（无 actor，纯 PC 互动）
# ═══════════════════════════════════════════════════════════════
DATASET_DESERT: MockDataset = {
    "dm_create": [
        {
            "hints": [
                "沙地上有巨大的足迹，看起来像是某种爬行动物留下的。",
                "远处的地平线上隐约能看到一座金字塔的轮廓。",
                "烈日当空，沙漠中的温度让人几乎喘不过气来。",
            ],
            "plot_brief": "冒险者们来到了灼热的沙漠，一座被遗忘的金字塔在地平线上若隐若现。",
            "scene_id": "desert",
        },
        {
            "hints": [
                "一具干尸被半埋在沙丘中，手里还紧握着一块刻有象形文字的泥板。",
                "沙漠中的风带着低语声，仿佛在诉说着千年前的故事。",
                "不远处的沙地上有一串脚印，通向一座被风化的石柱。",
            ],
            "plot_brief": "沙漠中隐藏着古老的秘密，风沙中传来低语，指引着冒险者前进。",
            "scene_id": "desert",
        },
        {
            "hints": [
                "沙丘顶部有一堆烧焦的骆驼骸骨，空气中残留着硫磺的味道。",
                "石柱上的浮雕描绘着长着翅膀的蛇，线条古朴而诡异。",
                "远处传来沉闷的鼓声，似乎从地下传来。",
            ],
            "plot_brief": "冒险者们发现沙漠深处似乎有某种古老的仪式正在进行。",
            "scene_id": "desert",
        },
    ],
    "dm_narrate": [
        {
            "narrative": "烈日如同一只燃烧的火炉悬在头顶，滚烫的沙粒在脚下发出细碎的摩擦声。放眼望去，无边无际的沙海在热浪中扭曲变形。远处，一座巨大的金字塔安静地矗立在沙漠中央，仿佛在等待它千年后的访客。几只秃鹫在高空盘旋，发出刺耳的鸣叫。",
        },
        {
            "narrative": "风沙低吼着掠过沙丘，带走了冒险者们的足迹。一座被风化的石柱群孤零零地立在沙漠中，上面模糊的象形文字在夕阳下泛着微弱的金光。空气干燥得让喉咙发痛，但更让人不安的是那种被注视的感觉——仿佛沙丘下面有什么东西在呼吸。",
        },
        {
            "narrative": "夜幕降临时，沙漠急促地冷却下来。漫天繁星映照在沙海上，寂静得只能听到风声。但在这片寂静中，隐约有鼓声从地下传来——有节奏，有力量，像是某种古老仪式的召唤。石柱上的浮雕在月光下呈现出诡异的轮廓。",
        },
    ],
    "talk": [
        {
            "turns": [
                {"speaker_id": "wizard", "text": "这个石柱上的象形文字……我好像在古籍里见过。"},
                {"speaker_id": "merchant", "text": "那是什么文字？能读懂吗？"},
                {
                    "speaker_id": "wizard",
                    "text": "古王国时期的神庙文字。这里记载着一位被封印的蛇神。",
                },
                {"speaker_id": "merchant", "text": "被封印？那最好不要碰这里的东西……"},
            ],
        },
        {
            "turns": [
                {"speaker_id": "fighter", "text": "看，沙地上有脚印，还很新！"},
                {"speaker_id": "guard", "text": "不是人的脚印……太大了。"},
                {"speaker_id": "fighter", "text": "你觉得是什么？沙虫？"},
                {"speaker_id": "guard", "text": "更糟。可能是守护者——就是古代法老留下的石像守卫。"},
            ],
        },
        {
            "turns": [
                {"speaker_id": "rogue", "text": "那座金字塔里面肯定有宝藏，我们进去看看。"},
                {
                    "speaker_id": "blacksmith",
                    "text": "我劝你不要。我祖父年轻时来过这里，他说金字塔会吃人。",
                },
                {"speaker_id": "rogue", "text": "吃人？怎么吃？"},
                {
                    "speaker_id": "blacksmith",
                    "text": "进去的人都没出来。只有一个活着回来了——但已经疯了。",
                },
            ],
        },
        {
            "turns": [
                {"speaker_id": "cleric", "text": "这片沙漠让我有一种说不出的不安感。"},
                {
                    "speaker_id": "merchant",
                    "text": "那是死亡魔法的残留。古王国时期的大法师喜欢用活人献祭。",
                },
                {"speaker_id": "cleric", "text": "献祭？这太邪恶了。"},
                {
                    "speaker_id": "merchant",
                    "text": "所以你如果看到地面上有黑色的印迹，千万别踩上去。",
                },
            ],
        },
        {
            "turns": [
                {"speaker_id": "wizard", "text": "那头骆驼的骸骨……烧得只剩骨头了。"},
                {"speaker_id": "guard", "text": "不是普通的火。是龙息。"},
                {"speaker_id": "wizard", "text": "这里怎么可能有龙？"},
                {
                    "speaker_id": "guard",
                    "text": "是沙龙——这里的传说。它能钻到地下，喷出的火焰比岩浆还烫。",
                },
            ],
        },
    ],
    "explore": [
        {
            "end_x": 12,
            "end_y": 15,
            "explore_record": "沙地上散落着几块碎裂的陶片，上面刻着与石柱相同的象形文字。",
        },
        {
            "end_x": 25,
            "end_y": 10,
            "explore_record": "一只蜥蜴从岩石缝隙中探出头，嘴里叼着一枚生锈的箭头。",
        },
        {
            "end_x": 8,
            "end_y": 25,
            "explore_record": "枯死的棕榈树旁有一个干涸的水井，井壁上攀附着发光的苔藓。",
        },
    ],
    "interact": [
        {
            "success": True,
            "narration": "他拂去石柱表面的沙尘，指尖沿着古老的刻文滑动。突然，一块石板轻轻下陷，露出一个隐藏的凹槽。",
        },
        {
            "success": False,
            "narration": "他试图推开沉重的石门，但门轴早已锈死。沙漠的风从缝隙中呼啸而过，发出低沉的呜咽。",
        },
        {
            "success": True,
            "narration": "他拧开古老的水壶盖，里面盛着的液体散发出一股草药清香——这是沙漠旅人用来抵御中暑的秘方。",
        },
    ],
    "combat": [
        {
            "narration": "他迎着沙龙喷出的烈焰冲出，长剑刺入怪物坚硬的鳞片缝隙，暗红的血液渗入黄沙。",
            "target_defeated": False,
            "result": "沙龙受创但更加狂暴",
        },
        {
            "narration": "蝎尾如闪电般袭来，他翻滚躲开，反手一箭射中了守护者的眼睛。",
            "target_defeated": True,
            "result": "蝎尾狮倒地不起",
        },
        {
            "narration": "他高举盾牌挡下石像守卫的重击，震得双臂发麻，但仍稳住身形挥出反击。",
            "target_defeated": False,
            "result": "石像守卫出现裂痕",
        },
    ],
    "actor_decision": [
        {
            "action_type": "talk",
            "target_id": "wizard",
            "target_type": "pc",
            "reasoning": "那个法师看起来对古代文字很感兴趣，可以给他指路。",
        },
        {
            "action_type": "talk",
            "target_id": "rogue",
            "target_type": "pc",
            "reasoning": "那个贼头贼脑的家伙想找宝藏，这沙漠里倒是有不少。",
        },
        {
            "action_type": "talk",
            "target_id": "fighter",
            "target_type": "pc",
            "reasoning": "这个战士看起来很勇敢，也许能帮我们对付沙龙的威胁。",
        },
    ],
    "reflection": [
        {
            "behavior_summary": "在沙漠中发现了古王国时期的石柱和象形文字，决定深入调查金字塔。",
            "insight": "这片沙漠曾是古王国的祭祀场所，有强大的魔法残留。",
        },
        {
            "behavior_summary": "找到了疑似沙龙的踪迹，需要准备应对大型生物的战斗方案。",
            "insight": "沙漠中的危险远不止气候——传说中的生物可能是真实存在的。",
        },
        {
            "behavior_summary": "从多方收集到金字塔的信息：有人进去了没出来，有奇怪的鼓声，还有黑色印记。",
            "insight": "金字塔是封印蛇神的场所，打破封印可能会释放它。",
        },
    ],
    "summarize": [
        {"summary": "冒险者进入沙漠，发现了古王国时期的遗迹和一座可疑的金字塔。"},
        {"summary": "沙漠中发现了巨大脚印和烧焦的骆驼骸骨，传说的沙龙可能真实存在。"},
        {"summary": "冒险者破译了石柱上的古文字，决定深入金字塔探索蛇神的秘密。"},
    ],
}

# ═══════════════════════════════════════════════════════════════
# 数据集 3：战斗线 / Combat storyline
# ═══════════════════════════════════════════════════════════════
# 包含战斗裁决 mock 数据 / Combat resolution mock data
DATASET_COMBAT: MockDataset = {
    "dm_create": [
        {
            "hints": [
                "灌木丛在无风的情况下摇晃了几下。",
                "地面上有明显的拖拽痕迹，通向林子深处。",
                "空气中有淡淡的血腥味。",
            ],
            "plot_brief": "冒险者们在林间小道上遭遇了伏击——一群地精从灌木丛后冲了出来。",
            "scene_id": "village_elderwood",
        },
        {
            "hints": [
                "篝火的余烬还在冒烟，看来敌人刚离开不久。",
                "树上钉着一支断裂的箭矢，箭杆上刻着陌生的图腾。",
                "远处传来战鼓声，节奏急促。",
            ],
            "plot_brief": "林间营地的废墟里，一群兽人斥候从树林中包围了过来。",
            "scene_id": "village_elderwood",
        },
        {
            "hints": [
                "地面上的蹄印很新鲜，是一大群生物踩出来的。",
                "空气中弥漫着一股强烈的麝香味——是食人魔的气味。",
                "几棵大树被连根拔起，树干上有巨大的抓痕。",
            ],
            "plot_brief": "一头愤怒的食人魔撞倒大树朝冒险者们冲来，后面跟着一群仆从。",
            "scene_id": "village_elderwood",
        },
    ],
    "dm_narrate": [
        {
            "narrative": "刚走到林中小路的拐弯处，一阵刺耳的尖啸打破了寂静。三个绿皮地精从灌木丛后跳了出来，挥舞着生锈的短剑和木棒，龇牙咧嘴地朝冒险者们冲来。他们的眼睛里闪着贪婪的光——看来是把这几个旅人当成了今天的猎物。",
        },
        {
            "narrative": "篝火旁的战斗来得很突然。兽人的战嚎在林间回荡，十几个绿皮肤的身影从树后和岩石后涌出。他们的獠牙在火光中泛着黄光，手中的斧头沾着干涸的血迹。领头的军阀骑在一头巨大的座狼上，咆哮着发起了冲锋。",
        },
        {
            "narrative": "大地震颤。一头超过三米高的食人魔撞断了碗口粗的树干，嘴里喷着粗气，挥舞着一根连根拔起的树干作为武器。它身后跟着一群遍体鳞伤的地精仆从，显然是被武力驱赶着上战场的。食人魔的目光锁定在冒险者们身上，发出震耳欲聋的怒吼。",
        },
    ],
    "talk": [
        {
            "turns": [
                {"speaker_id": "fighter", "text": "呱啊！人类！交出金币！"},
                {"speaker_id": "fighter", "text": "想得美，小怪物。拔剑吧！"},
            ],
        },
        {
            "turns": [
                {"speaker_id": "wizard", "text": "兽人军阀！你们为什么袭击这片森林？"},
                {"speaker_id": "guard", "text": "这森林现在是我们的了！人类滚出去！"},
                {"speaker_id": "wizard", "text": "森林属于生命，不属于任何人。"},
                {"speaker_id": "guard", "text": "那就用血来证明吧！"},
            ],
        },
        {
            "turns": [
                {"speaker_id": "rogue", "text": "我见过这家伙的图鉴——食人魔，弱点是眼睛！"},
                {"speaker_id": "fighter", "text": "你怎么不说弱点是脚趾？眼睛离地三米怎么打！"},
                {"speaker_id": "rogue", "text": "这不是在想办法嘛……脚趾也许行！"},
            ],
        },
    ],
    "combat": [
        {
            "narration": "地精尖叫着扑上来，他侧身避过生锈的短剑，反手一剑将敌人砍翻在地。",
            "target_defeated": True,
            "result": "地精倒地不起",
        },
        {
            "narration": "兽人军阀咆哮着挥下战斧，他举盾格挡，金属撞击声震耳欲聋，随即还以一记重击。",
            "target_defeated": False,
            "result": "兽人军阀受创但仍站立",
        },
        {
            "narration": "食人魔的树干带着风声砸下，他灵活地滚到怪物脚边，匕首深深刺入粗糙的脚踝。",
            "target_defeated": False,
            "result": "食人魔受创但仍在咆哮",
        },
    ],
    "actor_decision": [
        {
            "action_type": "combat",
            "target_id": "fighter",
            "target_type": "pc",
            "reasoning": "那个人类战士看起来最自信，先打垮他！",
        },
        {
            "action_type": "combat",
            "target_id": "cleric",
            "target_type": "pc",
            "reasoning": "先干掉治疗者，其他人就容易对付了。",
        },
        {
            "action_type": "combat",
            "target_id": "wizard",
            "target_type": "pc",
            "reasoning": "法师最危险，必须先解决掉。",
        },
    ],
    "reflection": [
        {
            "behavior_summary": "在森林中击退了地精的伏击，继续前行。",
            "insight": "这片森林可能被地精部落控制了，需要小心后续的埋伏。",
        },
        {
            "behavior_summary": "与兽人斥候部队发生了小规模战斗，成功突围。",
            "insight": "兽人也在扩张领地，这片森林成了多方势力的争夺焦点。",
        },
        {
            "behavior_summary": "艰难地击退了食人魔的攻击，收集了地精仆从提供的情报。",
            "insight": "食人魔通常不会主动袭击，背后可能有人在操纵。",
        },
    ],
    "summarize": [
        {"summary": "冒险者在森林中遭遇地精伏击，成功击退对手。"},
        {"summary": "林间营地遇到兽人斥候，经过激烈战斗后突围。"},
        {"summary": "一头食人魔袭击了冒险者，战斗中击败了它和它的地精仆从。"},
    ],
}

# ═══════════════════════════════════════════════════════════════
# 数据集注册 / Dataset registry
# ═══════════════════════════════════════════════════════════════
# 所有数据集注册表 / All datasets registry
# 数据集注册 / Dataset registry
DATASETS: dict[str, MockDataset] = {
    "tavern": DATASET_TAVERN,
    "desert": DATASET_DESERT,
    "combat": DATASET_COMBAT,
}

DEFAULT_DATASET = "tavern"  # 默认数据集


# ═══════════════════════════════════════════════════════════════
# 通用池（跨数据集的 talk / actor_decision / reflection / summarize）
# ═══════════════════════════════════════════════════════════════
# 跨数据集共享池 / Cross-dataset shared pool — aggregates all dataset keys
_POOL: dict[str, list[dict]] = {}
for _ds in DATASETS.values():
    for _key, _examples in _ds.items():
        if _key not in _POOL:
            _POOL[_key] = []
        _POOL[_key].extend(_examples)


def get_dataset(name: str = "") -> MockDataset:
    return DATASETS.get(name, DATASETS[DEFAULT_DATASET])


# 随机抽取 mock 数据 / Randomly fetch mock data for a purpose


def get_mock(purpose: str, dataset_name: str = "") -> dict:
    """获取某个 purpose 的 mock 数据——随机抽取一个示例。

    pc_decision 使用轮转池，保证覆盖 talk/explore/interact。
    dm_create / dm_narrate 限定数据集（每个数据集有不同的场景和叙事风味）。
    其他 purpose（talk / actor_decision / reflection / summarize）跨数据集随机。
    """
    if purpose == "pc_decision":
        return _pc_rotator.next()

    # 所有 purpose 跨数据集随机池 / All purposes: cross-dataset random pool
    pool = _POOL.get(purpose, [])
    return random.choice(pool) if pool else {}
