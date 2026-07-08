"""Mock 数据集——多示例随机抽取，每个数据集自包含完整的决策+行动数据。"""

import random

MockDataset = dict[str, list[dict]]


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
            "narration": "他仔细检查目标，在夹层中找到一卷泛黄的羊皮纸——上面用褪色的墨水标着一条通往北方森林的隐秘小径。",
        },
        {
            "success": False,
            "narration": "他试图强行打开，但锁扣纹丝不动——铁栓从内侧卡死了，除非找到对应的钥匙或另寻他路。",
        },
        {
            "success": True,
            "narration": "机关应声弹开，里面露出一枚刻着龙纹的徽章和一小袋金币——看起来是某位冒险者留下的应急储备。",
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
            "thought": "这些冒险者装备精良，生意来了。DM 让我留意打听商队消息的人。",
        },
        {
            "action_type": "talk",
            "target_id": "fighter",
            "target_type": "pc",
            "thought": "终于看到实力不错的冒险者了，得把北边的情况告诉他们。",
        },
        {
            "action_type": "talk",
            "target_id": "rogue",
            "target_type": "pc",
            "thought": "那个贼头贼脑的家伙看起来对秘密很感兴趣，正好可以利用他。",
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
    "pc_decision": [
        {
            "action": {
                "action_type": "talk",
                "target_id": "merchant",
                "target_type": "actor",
                "thought": "Greta 的眼神暗示她有话要说，先打听一下最近镇上有什么异常。",
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "酒馆角落的木板微微翘起，下面似乎藏着什么。去检查一下。",
                "explore_x": 10,
                "explore_y": 12,
            }
        },
        {
            "action": {
                "action_type": "talk",
                "target_id": "blacksmith",
                "target_type": "actor",
                "thought": "铁匠看起来是个有故事的人，去和他聊聊也许能打听到什么。",
            }
        },
        {
            "action": {
                "action_type": "interact",
                "target_id": "chest_1",
                "target_type": "scene_object",
                "thought": "角落里那个箱子看起来有点可疑，让我检查一下里面有什么。",
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "酒馆后门有点异样，顺着一串湿脚印去小巷深处看看。",
                "explore_x": 8,
                "explore_y": 15,
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "窗台上有积满灰尘的陶罐，也许里面有什么线索。",
                "explore_x": 12,
                "explore_y": 8,
            }
        },
        {
            "action": {
                "action_type": "talk",
                "target_id": "guard",
                "target_type": "actor",
                "thought": "门口的守卫似乎欲言又止，去和他打探一下消息。",
            }
        },
        {
            "action": {
                "action_type": "interact",
                "target_id": "door_cellar",
                "target_type": "scene_object",
                "thought": "那个通往地窖的门虚掩着，说不定下面有什么好东西。",
            }
        },
        {
            "action": {
                "action_type": "combat",
                "target_id": "goblin",
                "target_type": "actor",
                "thought": "那只地精一直躲在木桶后面窥视，肯定不怀好意。先拔剑把它逼出来。",
            }
        },
        {
            "action": {
                "action_type": "combat",
                "target_id": "skeleton",
                "target_type": "actor",
                "thought": "角落里那具骸骨突然动了一下——不死生物不能留。",
            }
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
            "narration": "他拨开木箱表面的浮尘，铜锁早已锈蚀。轻轻一推，箱盖应声翻开——里面躺着一卷用麻绳扎紧的羊皮纸和半枚刻着蛇纹的铜币。",
        },
        {
            "success": False,
            "narration": "他试图撬开木箱侧面的暗格，但机关已经卡死了——也许是沙粒堵塞了滑轨。需要先清理缝隙里的积沙。",
        },
        {
            "success": True,
            "narration": "他在箱底摸到一层夹层。撕开衬布，里面藏着一张画着星象图的牛皮纸——标注的位置刚好指向金字塔的方向。",
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
            "thought": "那个法师看起来对古代文字很感兴趣，可以给他指路。",
        },
        {
            "action_type": "talk",
            "target_id": "rogue",
            "target_type": "pc",
            "thought": "那个贼头贼脑的家伙想找宝藏，这沙漠里倒是有不少。",
        },
        {
            "action_type": "talk",
            "target_id": "fighter",
            "target_type": "pc",
            "thought": "这个战士看起来很勇敢，也许能帮我们对付沙龙的威胁。",
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
    "pc_decision": [
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "沙地上散落着碎裂的陶片，上面刻着象形文字。去看看石柱附近有没有更多线索。",
                "explore_x": 12,
                "explore_y": 15,
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "一只蜥蜴叼着生锈的箭头钻进岩石缝隙，附近说不定有古代战场遗迹。",
                "explore_x": 25,
                "explore_y": 10,
            }
        },
        {
            "action": {
                "action_type": "talk",
                "target_id": "merchant",
                "target_type": "actor",
                "thought": "沙漠商人似乎知道古王国时期的历史，去打听一下石柱的秘密。",
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "枯死的棕榈树旁有一口干涸的水井，井壁上似乎有发光的苔藓。过去看看。",
                "explore_x": 8,
                "explore_y": 25,
            }
        },
        {
            "action": {
                "action_type": "talk",
                "target_id": "guard",
                "target_type": "actor",
                "thought": "守卫知道沙漠里的危险，向他打听一下前方的路况。",
            }
        },
        {
            "action": {
                "action_type": "interact",
                "target_id": "chest_wooden",
                "target_type": "scene_object",
                "thought": "石柱下方有一个古旧的木箱，上面雕刻着奇怪的符文。",
            }
        },
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
            "narration": "骷髅从黑暗中冲出，骨爪带着腐朽的劲风扫向他的咽喉。他闪身避开，反手一记重击将骨架劈成两段。",
            "target_defeated": True,
            "result": "骷髅散架倒地",
        },
        {
            "narration": "兽人首领咆哮着挥下双手战斧，他举盾格挡，金属撞击声震耳欲聋，随即还以一记重击劈进对方的肩甲。",
            "target_defeated": False,
            "result": "兽人首领受创但仍在咆哮",
        },
    ],
    "actor_decision": [
        {
            "action_type": "combat",
            "target_id": "fighter",
            "target_type": "pc",
            "thought": "那个人类战士看起来最自信，先打垮他！",
        },
        {
            "action_type": "combat",
            "target_id": "cleric",
            "target_type": "pc",
            "thought": "先干掉治疗者，其他人就容易对付了。",
        },
        {
            "action_type": "combat",
            "target_id": "wizard",
            "target_type": "pc",
            "thought": "法师最危险，必须先解决掉。",
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
    "explore": [
        {
            "end_x": 20,
            "end_y": 15,
            "explore_record": "树林边缘的灌木丛里散落着几支断裂的箭矢和一块被丢弃的兽皮盾牌。",
        },
    ],
    "pc_decision": [
        {
            "action": {
                "action_type": "combat",
                "target_id": "goblin",
                "target_type": "actor",
                "thought": "那只地精虎视眈眈，蹲在灌木丛后准备突袭。必须先下手为强，拔剑冲锋！",
            }
        },
        {
            "action": {
                "action_type": "combat",
                "target_id": "skeleton",
                "target_type": "actor",
                "thought": "不死生物不能放任它在村子里游荡，必须用圣光净化它。",
            }
        },
        {
            "action": {
                "action_type": "combat",
                "target_id": "orc_boss",
                "target_type": "actor",
                "thought": "兽人首领才是威胁的根源，集中火力解决它，其他喽啰自然会溃散。",
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "战斗结束后巡视林中营地，看看有没有战利品或敌人的侦察情报。",
                "explore_x": 20,
                "explore_y": 15,
            }
        },
    ],
    "interact": [
        {
            "success": True,
            "narration": "他从倒下的兽人军阀腰带上扯下一块金属徽章——这是战帮的信物，拿着它可以伪装身份通过前方的哨站。",
        },
        {
            "success": False,
            "narration": "营地的铁笼被粗铁链锁死，里面关着的不是俘虏而是几只饿疯了的座狼——它们撞得铁笼摇摇欲坠。",
        },
    ],
}

# ═══════════════════════════════════════════════════════════════
# 数据集 4：蔚蓝镇 / Azure Town
# ═══════════════════════════════════════════════════════════════
DATASET_AZURE_TOWN: MockDataset = {
    "dm_create": [
        {
            "hints": [
                "市政厅前的告示板上贴着一张新告示，墨迹还未干透。",
                "花店门口的老妇人一边浇花一边偷偷打量路过的冒险者。",
                "镇子东边的石砖路面上有几道新鲜的马车辙印，一直延伸到镇外。",
            ],
            "plot_brief": "蔚蓝镇的街道在晨光中显得宁静祥和，但冒险者们能察觉到一丝不安在空气中蔓延。",
            "scene_id": "azure_town",
        },
        {
            "hints": [
                "铁匠铺的烟囱冒着浓烟，里面传来急促的敲打声。",
                "几个村民聚在井边低声议论着什么，看到冒险者走近就散开了。",
                "市政厅二楼的窗户里透出摇曳的烛光，似乎有人在连夜办公。",
            ],
            "plot_brief": "蔚蓝镇的居民们似乎被什么困扰着，连平日里热闹的集市都冷清了许多。",
            "scene_id": "azure_town",
        },
        {
            "hints": [
                "镇口的路牌被人刻意歪斜，上面的字迹模糊不清。",
                "花店的橱窗里摆着一束枯萎的黑玫瑰，花茎上缠着奇怪的丝线。",
                "远处的教堂钟声比平时晚了一个小时才敲响。",
            ],
            "plot_brief": "蔚蓝镇看似平静的外表下，一场暗流正在涌动。冒险者们踏入了这场未知的风暴中心。",
            "scene_id": "azure_town",
        },
    ],
    "dm_narrate": [
        {
            "narrative": "晨光洒在蔚蓝镇的石砖街道上，花店门口的老妇人微笑着向路人点头致意。然而当她看到冒险者们走近时，眼神里闪过一丝复杂的情绪——像是警告，又像是在求救。铁匠铺的锤击声戛然而止，整个街道陷入了短暂的寂静。"
        },
        {
            "narrative": "市政厅前的告示板在风中轻轻摇晃，一张新张贴的羊皮纸上用红墨水写着「悬赏：北哨塔异常火光」。几个村民围在告示板前交头接耳，但看到冒险者们走来，立刻散去了。花店的老妇人叹了口气，继续浇着那些已经枯萎的花朵。"
        },
        {
            "narrative": "蔚蓝镇的黄昏来得格外昏沉。铁匠关了铺子，花店收了摊，连街头的流浪猫都不见了踪影。只有冒险者们的脚步声在空旷的石砖街道上回荡。市政厅二楼的烛光忽明忽暗，像是一个不安的信号。"
        },
    ],
    "talk": [
        {
            "turns": [
                {"speaker_id": "cleric", "text": "请问，镇上最近发生了什么事？"},
                {
                    "speaker_id": "merchant",
                    "text": "你是外来人吧。北边的哨塔夜里总有火光，还有人听到过奇怪的嚎叫声。",
                },
                {"speaker_id": "cleric", "text": "有人去调查过吗？"},
                {
                    "speaker_id": "merchant",
                    "text": "镇长派了一支巡逻队，但……他们再也没回来。现在大家都绕着哨塔走。",
                },
            ],
        },
        {
            "turns": [
                {"speaker_id": "wizard", "text": "这些黑玫瑰是哪里来的？看起来不太寻常。"},
                {
                    "speaker_id": "merchant",
                    "text": "是北边废墟里采的。那地方的玫瑰全是黑色的，而且……只在满月时开花。",
                },
                {"speaker_id": "wizard", "text": "有意思，这花茎上缠绕的丝线是什么材料？"},
                {
                    "speaker_id": "merchant",
                    "text": "不知道，但碰了这花的人都说晚上会做同样的噩梦。",
                },
            ],
        },
    ],
    "explore": [
        {
            "end_x": 18,
            "end_y": 8,
            "explore_record": "顺着马车辙印走到镇口，发现路牌被人刻意用铁钉改变了指向——箭头正对着北边哨塔的方向。",
        },
        {
            "end_x": 12,
            "end_y": 13,
            "explore_record": "喷泉池底沉着一枚铜质徽章，边缘刻着「蔚蓝守望」四个字，但表面已经被刮花了。",
        },
        {
            "end_x": 30,
            "end_y": 4,
            "explore_record": "镇外小山坡上有一片新翻的土堆，扒开土层露出一个铁匣，里面装着几卷空白羊皮纸。",
        },
    ],
    "interact": [
        {
            "success": True,
            "narration": "暗门缓缓打开，一股混合着泥土和陈年木材的气味扑面而来。角落里整齐地堆着几只陶罐，其中一只底部压着一张泛黄的纸条。",
        },
        {
            "success": False,
            "narration": "他试图撬开铁栅门，但锁芯已被锈蚀得无法转动——需要特制的钥匙或者强效腐蚀性药水才能打开。",
        },
    ],
    "combat": [
        {
            "narration": "他从花丛后闪出，一剑劈开偷袭者的短矛，随即反击将其击退。",
            "target_defeated": True,
            "result": "袭击者倒地",
        },
    ],
    "actor_decision": [
        {
            "action_type": "talk",
            "target_id": "rogue",
            "target_type": "pc",
            "thought": "那个贼头贼脑的人一直在打量花店——他可能在找我藏在玫瑰丛下的东西。",
        },
        {
            "action_type": "talk",
            "target_id": "cleric",
            "target_type": "pc",
            "thought": "牧师身上的圣徽不对劲，它在靠近黑玫瑰时会发光。得警告他们。",
        },
        {
            "action_type": "combat",
            "target_id": "fighter",
            "target_type": "pc",
            "thought": "那个重甲战士堵住了哨塔的路口，必须引开他。",
        },
    ],
    "reflection": [
        {
            "behavior_summary": "镇口路牌被篡改指向北边坡地，顺着车辙发现了铁匣和空白羊皮纸。",
            "insight": "哨塔的异常火光和黑玫瑰可能有关联——有人在掩盖什么。",
        },
    ],
    "summarize": [
        {"summary": "蔚蓝镇的冒险者发现了被篡改的路牌和花店老妇人的秘密，哨塔的悬赏还没解开。"},
    ],
    "pc_decision": [
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "镇口的路牌被人动了手脚，这不是偶然。顺着马车辙印出去看看，车辙指向了北边坡地。",
                "explore_x": 18,
                "explore_y": 8,
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "喷泉池水干了，池底似乎有金属反光。去看看池底有什么东西。",
                "explore_x": 12,
                "explore_y": 13,
            }
        },
        {
            "action": {
                "action_type": "talk",
                "target_id": "merchant",
                "target_type": "actor",
                "thought": "花店的老妇人看起来知道些什么，她一直在偷偷观察我们。去问问她关于黑玫瑰和哨塔的事。",
            }
        },
        {
            "action": {
                "action_type": "interact",
                "target_id": "door_cellar",
                "target_type": "scene_object",
                "thought": "花店后面的地窖门半掩着，里面有微弱的光透出来。也许那里藏着不为人知的秘密。",
            }
        },
    ],
}

# ═══════════════════════════════════════════════════════════════
# 数据集 5：塔巴镇 / Taba Town
# ═══════════════════════════════════════════════════════════════
DATASET_TABA_TOWN: MockDataset = {
    "dm_create": [
        {
            "hints": [
                "镇中心的喷泉已经干涸，池底堆满了落叶和灰尘。",
                "路边的房屋大多门窗紧闭，只有一户人家的烟囱还冒着炊烟。",
                "公告牌上贴满了各种告示——寻人启事、通缉令、还有一张古怪的占卜广告。",
            ],
            "plot_brief": "塔巴镇曾经是个繁荣的贸易枢纽，但如今街道空荡，空气中弥漫着一种说不清的紧张感。",
            "scene_id": "taba_town",
        },
        {
            "hints": [
                "通往郊外的土路上散布着凌乱的脚印，有人类的，也有某种更大的生物。",
                "镇子西边传来一声沉闷的爆炸声，然后是什么东西坍塌的声响。",
                "一个小孩躲在墙角后面朝冒险者们招手，似乎想告诉他们什么。",
            ],
            "plot_brief": "塔巴镇的地下似乎有什么东西在活动，地面不时传来轻微的震动。",
            "scene_id": "taba_town",
        },
        {
            "hints": [
                "草地在无风的情况下剧烈摇晃，像是有什么东西在里面快速移动。",
                "镇上的老钟楼敲了十三下——明明是正午，却敲了十三下。",
                "杂货店的招牌掉在地上摔成了两半，上面有被爪子抓过的痕迹。",
            ],
            "plot_brief": "塔巴镇的异常越来越明显，连最迟钝的村民都开始收拾行李准备逃离。",
            "scene_id": "taba_town",
        },
    ],
    "dm_narrate": [
        {
            "narrative": "塔巴镇的街道比预想的要空旷得多。曾经热闹的喷泉广场如今只剩几只鸽子在池边徘徊，石砖缝里长出了野草。一个老人在自家门廊下朝冒险者们挥了挥手，示意他们过去——他的表情里混杂着恐惧和一丝不合时宜的希望。"
        },
        {
            "narrative": "冒险者们刚走到镇中心，脚底传来一阵低沉的轰鸣，仿佛有什么巨大的东西从地下深处经过。喷泉里残存的水面泛起了一圈圈涟漪。几扇窗户应声震碎，玻璃渣落在无人的街道上，发出清脆的声响。"
        },
        {
            "narrative": "夜幕降临时，塔巴镇完全变了个样。炉火全部熄灭，没有任何一盏灯亮着。月光照在干涸的喷泉上，在池底映出一个模糊的符号——像是有人用粉笔匆忙画下的。远处，东边森林里传来一声悠长的嚎叫，紧接着是更多的嚎叫回应。"
        },
    ],
    "explore": [
        {
            "end_x": 35,
            "end_y": 20,
            "explore_record": "东边森林边缘倒着几棵被连根拔起的大树，树干上有粗壮利爪留下的深沟。",
        },
        {
            "end_x": 15,
            "end_y": 45,
            "explore_record": "镇子南边的老磨坊水车仍在转动，但整座建筑已经倾斜——地基下似乎被什么东西掏空了。",
        },
        {
            "end_x": 45,
            "end_y": 30,
            "explore_record": "后山里发现一个被藤蔓覆盖的矿坑入口，坑道深处传来微弱的敲击声。",
        },
    ],
    "talk": [
        {
            "turns": [
                {"speaker_id": "fighter", "text": "老人家，镇上的人都去哪了？"},
                {
                    "speaker_id": "guard",
                    "text": "都躲在家里呢。地底下有东西在挖洞，昨晚连教堂的地基都被掏空了一块。",
                },
                {"speaker_id": "fighter", "text": "什么东西？"},
                {
                    "speaker_id": "guard",
                    "text": "不知道。但它每次经过，地面就会震动——就像心跳一样有规律。",
                },
            ],
        },
    ],
    "combat": [
        {
            "narration": "地面突然隆起，一只覆盖着甲壳的巨大蠕虫从土中冲出。他侧身闪过黏液喷吐，环首刀狠狠劈进虫体的关节处。",
            "target_defeated": True,
            "result": "掘地蠕虫缩回地下",
        },
    ],
    "interact": [
        {
            "success": True,
            "narration": "他撬开喷泉池底的暗格，池水从裂缝中涌出——不是普通的水，而是带着微弱荧光的蓝色液体。",
        },
        {
            "success": False,
            "narration": "暗格盖板被厚重的石板从下方顶住了。推开需要更大的力量——或者找到控制石板升降的旁路机关。",
        },
    ],
    "actor_decision": [
        {
            "action_type": "combat",
            "target_id": "rogue",
            "target_type": "pc",
            "thought": "那个敏捷的家伙跑到磨坊下面去了——不能让他发现矿井的入口。",
        },
        {
            "action_type": "combat",
            "target_id": "wizard",
            "target_type": "pc",
            "thought": "法师在感应地下的震动，如果让他完全施法可能会惊醒深处的巢穴之主。",
        },
    ],
    "reflection": [
        {
            "behavior_summary": "在森林边缘发现了被利爪连根拔起的大树，磨坊地基也被掏空了。",
            "insight": "地底的巨型生物正在向镇子方向移动——它的掘进路线是一条直线，目标似乎是钟楼。",
        },
    ],
    "summarize": [
        {"summary": "塔巴镇的冒险者发现镇子地下有巨型蠕虫在活动，钟楼成了它的目标。"},
    ],
    "pc_decision": [
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "东边森林里传来的嚎叫声越来越近，那些被连根拔起的大树一定和这些声音有关。",
                "explore_x": 35,
                "explore_y": 20,
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "南边老磨坊附近的地面有异常的塌陷，可能地下有通道。去看看塌陷有多深。",
                "explore_x": 15,
                "explore_y": 45,
            }
        },
        {
            "action": {
                "action_type": "talk",
                "target_id": "guard",
                "target_type": "actor",
                "thought": "那个朝我们招手的老人在门廊下守着，也许他知道镇子地下到底是什么东西在活动。",
            }
        },
        {
            "action": {
                "action_type": "interact",
                "target_id": "door_cellar",
                "target_type": "scene_object",
                "thought": "喷泉池底那个暗格可能有机关。检查看看下面是不是通向地下的入口。",
            }
        },
    ],
}

# ═══════════════════════════════════════════════════════════════
# 数据集 6：蜘蛛棉花隧道 / Spyder Cotton Tunnel
# ═══════════════════════════════════════════════════════════════
DATASET_TUNNEL: MockDataset = {
    "dm_create": [
        {
            "hints": [
                "隧道深处传来水滴声，每滴一声，周围就暗一分。",
                "墙壁上覆盖着一层黏滑的丝状物，碰到皮肤会微微发麻。",
                "地上散落着被啃得干干净净的骨头，有些上面还有细密的咬痕。",
            ],
            "plot_brief": "冒险者们钻进了狭窄的隧道，潮湿的空气里混杂着腐肉和某种昆虫分泌物的酸臭味。",
            "scene_id": "spyder_cotton_tunnel",
        },
        {
            "hints": [
                "隧道天花板上有大面积的蛛网，其中一张网里裹着一具穿着盔甲的遗骸。",
                "从深处传来的嘶嘶声越来越近，夹杂着某种硬壳生物爬行的声音。",
                "隧道旁边有一条人工开凿的岔路，入口处立着一块褪色的警告牌。",
            ],
            "plot_brief": "隧道逐渐变宽，前方出现了一个巨大的地下洞穴，洞穴中央有什么东西在黑暗中闪烁。",
            "scene_id": "spyder_cotton_tunnel",
        },
        {
            "hints": [
                "洞穴地面覆盖着一层厚厚的虫卵，有的已经开始孵化。",
                "一具被蛛丝完全包裹的尸体靠在墙边，手边散落着一本日记。",
                "洞穴顶部垂下的一根钟乳石上刻着古老的矮人符文。",
            ],
            "plot_brief": "冒险者们发现了蜘蛛巢穴的核心——一个被蛛丝覆盖的矮人遗迹，里面藏着某种古老的秘密。",
            "scene_id": "spyder_cotton_tunnel",
        },
    ],
    "dm_narrate": [
        {
            "narrative": "隧道入口只容一人弯腰通过，潮湿的石壁上布满了发光的苔藓，勉强照亮了前路。冒险者们刚走进去几十步，身后的入口就被一片阴影遮住了——不是石头，而是某种巨大的、正在移动的身体。现在已经没有回头路了，深处传来一阵令人牙酸的啃噬声。"
        },
        {
            "narrative": "洞穴豁然开朗。冒险者们发现自己站在一个被挖空的巨大空间里，四周的墙壁上覆盖着数不清的蛛网。蛛网的中央，一个足有两人大的蜘蛛正用复眼打量着这群不速之客。它的口器里还叼着半截人类的腿骨，骨髓正一滴一滴地落在虫卵堆上。"
        },
        {
            "narrative": "隧道最深处出乎意料地安静。无数蛛丝织成了精细的帷幕，将一块刻满矮人符文的石碑围在中央。蜘蛛们似乎在保护——或者说看守——这个遗迹。石碑上最后一排符文在黑暗中微微发光，像是在回应某种召唤。"
        },
    ],
    "explore": [
        {
            "end_x": 10,
            "end_y": 5,
            "explore_record": "隧道墙壁上渗出一层薄薄的水膜，指尖划过能感觉到微弱的脉搏——像是洞穴本身在呼吸。",
        },
        {
            "end_x": 25,
            "end_y": 10,
            "explore_record": "一堆碎石后面露出半截铁镐——这不是矿工的镐，上面刻着矮人王国的纹章。",
        },
        {
            "end_x": 15,
            "end_y": 15,
            "explore_record": "地面有一个被黏液填满的小坑，黏液里泡着一把还发着光的匕首，刀身符文轻轻震动。",
        },
    ],
    "talk": [
        {
            "turns": [
                {"speaker_id": "rogue", "text": "这些蛛丝太粘了，踩上去会被缠住。"},
                {
                    "speaker_id": "wizard",
                    "text": "别碰那些丝线——它们是活的。每一根丝都在把地面的震动传回巢穴深处。",
                },
                {"speaker_id": "rogue", "text": "你的意思是……它已经知道我们来了？"},
                {
                    "speaker_id": "wizard",
                    "text": "从我们踏进洞口的第一步起，它就在数我们的人数了。",
                },
            ],
        },
    ],
    "interact": [
        {
            "success": True,
            "narration": "他小心翼翼地用匕首割下一截蛛丝，丝线在刀刃上发出微弱的荧光。这是一种罕见的洞穴蜘蛛丝——炼金术师愿意为它付出高价。",
        },
        {
            "success": False,
            "narration": "石碑上的矮人符文突然剧烈发光，一阵灼热的冲击波将他弹开。石碑表面浮现出一行警告文字：「只有符文之锤的持有者方可触碰」。",
        },
    ],
    "combat": [
        {
            "narration": "被蛛丝包裹的骷髅猛地挣断最后一根丝线，空洞的眼眶锁定了他。他抢在骷髅挥下骨剑之前，用剑柄狠狠砸碎了它的脊椎——骨头碎片和蛛丝一同散落在地上。",
            "target_defeated": True,
            "result": "蛛丝骷髅散架倒地",
        },
    ],
    "actor_decision": [
        {
            "action_type": "combat",
            "target_id": "fighter",
            "target_type": "pc",
            "thought": "那个穿重甲的人走得最慢——从天花板垂降到敌人身后，准备给战士致命一击。",
        },
        {
            "action_type": "combat",
            "target_id": "wizard",
            "target_type": "pc",
            "thought": "法师手里的灯光暴露了所有人的位置。先解决掉光源。",
        },
    ],
    "reflection": [
        {
            "behavior_summary": "在隧道中发现了矮人王国留下的铁镐和石碑，碑上的符文发光但触碰不了。",
            "insight": "这座洞穴曾经是矮人的矿场，蜘蛛入侵后矮人撤退了——但留下了某种力量的守护。",
        },
    ],
    "summarize": [
        {"summary": "冒险者进入蜘蛛隧道，发现了矮人遗迹和发光的符文石碑。"},
    ],
    "pc_decision": [
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "蜘蛛都在巢穴深处，现在洞口附近比较安静。趁它们没注意到我们，先摸清这条隧道的结构和退路。",
                "explore_x": 10,
                "explore_y": 5,
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "碎石堆后面露出金属的反光，可能是什么工具或武器。爬过去看看那些年代久远的铁镐。",
                "explore_x": 25,
                "explore_y": 10,
            }
        },
        {
            "action": {
                "action_type": "combat",
                "target_id": "skeleton",
                "target_type": "actor",
                "thought": "那个被蛛丝包裹的遗骸突然动了一下——不是幻觉，它正在缓慢地站起来。趁它还没完全挣脱蛛丝，先下手为强。",
            }
        },
        {
            "action": {
                "action_type": "interact",
                "target_id": "door_cellar",
                "target_type": "scene_object",
                "thought": "石碑上的矮人符文和蛛丝之间有某种联系。试试用匕首割一截蛛丝触碰石碑。",
            }
        },
    ],
}

# ═══════════════════════════════════════════════════════════════
# 数据集 7：水域大教堂 / Water Cathedral
# ═══════════════════════════════════════════════════════════════
DATASET_CATHEDRAL: MockDataset = {
    "dm_create": [
        {
            "hints": [
                "水面上漂浮着几片残破的彩窗碎片，阳光透过水面的折射在水中映出斑斓的色彩。",
                "大教堂的穹顶有一半沉在水下，另一半露出水面的部分长满了藤壶和水藻。",
                "清澈的水下能看到一条向下的石阶，阶梯两侧立着长满青苔的雕像。",
            ],
            "plot_brief": "冒险者们来到了一座半沉于水中的古老教堂，碧蓝的水面下隐约可见建筑的宏伟轮廓。",
            "scene_id": "water_cathedral",
        },
        {
            "hints": [
                "教堂中殿的祭坛上放着一把生锈的钥匙，钥匙上刻着浪花图案。",
                "水下的彩色玻璃窗上描绘着一场古老的仪式——祭司们将某物沉入海底。",
                "从深水区传来悠扬的吟唱声，如泣如诉，像是教堂唱诗班的回响。",
            ],
            "plot_brief": "水下的教堂隐藏着古老的秘密，每一片彩窗都讲述着被淹没的历史。",
            "scene_id": "water_cathedral",
        },
        {
            "hints": [
                "祭坛下方有一个漆黑的洞口，冰凉的暗流从里面不断涌出。",
                "墙壁上镶嵌的贝壳在自动排列，组成了一个螺旋状的图案。",
                "水面上突然浮起一串气泡，从最深的那个洞口里飘上来。",
            ],
            "plot_brief": "教堂最深处有一个通往未知领域的入口，冰冷的暗流似乎在阻止冒险者们靠近。",
            "scene_id": "water_cathedral",
        },
    ],
    "dm_narrate": [
        {
            "narrative": "脚下是及膝的碧水，头顶是半塌的穹顶。阳光穿过残破的彩窗在水面上投下破碎的光斑，仿佛整座教堂都沉浸在一个巨大的水族箱里。石柱上爬满了发光的海藻，在水中轻轻摇曳。冒险者们的脚步声在水面上激起圈圈涟漪，向四周扩散而去。"
        },
        {
            "narrative": "冒险者们涉水走过中殿，水下一面完整的彩色玻璃窗吸引了所有人的目光。上面描绘的场景令人不寒而栗：一群穿着长袍的祭司将一尊黑色的雕像沉入深海，而海面上方，巨大的触手正撕破云层探下。彩窗底部刻着一行被水垢覆盖的文字，隐约能辨认出「不要惊醒沉睡者」。"
        },
        {
            "narrative": "从教堂最深处的洞口中涌出一股冰冷的水流，像是这座建筑在呼吸。水面突然剧烈沸腾，一串拳头大的气泡从黑洞中冒出。紧接着，一阵低沉的嗡鸣从水底传来——那不是自然的声音，更像是某种古老机器的齿轮在水下重新开始转动。贝壳形成的螺旋图案开始慢慢发光。"
        },
    ],
    "explore": [
        {
            "end_x": 28,
            "end_y": 15,
            "explore_record": "珊瑚覆盖的凹室里嵌着一枚古老的贝壳护符——上面刻着和海战中浮雕相同的祭司纹章。",
        },
        {
            "end_x": 12,
            "end_y": 10,
            "explore_record": "浅水区的水底铺着一层细沙，沙子下面隐约可见马赛克拼贴的图案碎片。",
        },
        {
            "end_x": 35,
            "end_y": 25,
            "explore_record": "一根断裂的石柱斜靠在墙上，柱身的浮雕描绘着一场古老的海战。",
        },
        {
            "end_x": 20,
            "end_y": 30,
            "explore_record": "水面倒影中浮现出一张不属于任何冒险者的脸——它嘴唇翕动，似乎在念一段祷文。",
        },
    ],
    "talk": [
        {
            "turns": [
                {
                    "speaker_id": "cleric",
                    "text": "这座教堂……被淹没了至少一百年。但为什么蜡烛还在燃烧？",
                },
                {
                    "speaker_id": "wizard",
                    "text": "不是蜡烛，是魔法。水源源不断地供给着某种维持法术——把整座建筑封印在时间里。",
                },
                {"speaker_id": "cleric", "text": "封印什么？"},
                {
                    "speaker_id": "wizard",
                    "text": "彩窗上画的那种东西。那些祭司不是把雕像沉入海里——他们是在用教堂压住它。",
                },
            ],
        },
    ],
    "interact": [
        {
            "success": True,
            "narration": "他把锈蚀的钥匙插入石板缝隙，石板缓缓下沉，底部竟是一块纯金打造的封蜡——上面龙飞凤舞地签着五个名字，最后一个名字的墨迹还未干透。",
        },
        {
            "success": False,
            "narration": "他试图用手推开水下的石阶闸门，但水压加上锈蚀让闸门纹丝不动——可能需要找到泄水机关。",
        },
    ],
    "combat": [
        {
            "narration": "水中突然伸出一条半透明的触手，卷向他的脚踝。他挥剑斩断触手，断裂处涌出黑色的冷雾，雾中浮现无数张扭曲的脸。",
            "target_defeated": False,
            "result": "触手缩回黑暗，但更多在黑暗中涌动",
        },
    ],
    "actor_decision": [
        {
            "action_type": "combat",
            "target_id": "cleric",
            "target_type": "pc",
            "thought": "圣光刺痛了我的眼睛，那个牧师必须死。",
        },
        {
            "action_type": "combat",
            "target_id": "wizard",
            "target_type": "pc",
            "thought": "法师在读彩窗上的文字——他知道得太多了，不能让他继续。",
        },
    ],
    "reflection": [
        {
            "behavior_summary": "找到了贝壳护符和断裂石柱上的海战浮雕，确认了祭司封印的事件。",
            "insight": "教堂是封印，不是建筑。每当水源衰减，封印就会减弱——我们来的正是时候。",
        },
    ],
    "summarize": [
        {"summary": "冒险者涉水探索被淹没的古老教堂，发现这里其实是一座封印——压着某种深海之物。"},
    ],
    "pc_decision": [
        {
            "action": {
                "action_type": "interact",
                "target_id": "door_cellar",
                "target_type": "scene_object",
                "thought": "祭坛上那把刻着浪花的钥匙一定对应着某扇门。去检查周围有没有被水淹没的锁孔或机关。",
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "贝壳螺旋图案指向的那个方向有一个被珊瑚覆盖的凹室。先去那边看看是否有通往更深层的入口。",
                "explore_x": 28,
                "explore_y": 15,
            }
        },
        {
            "action": {
                "action_type": "explore",
                "target_id": None,
                "target_type": None,
                "thought": "浅水区水底的马赛克拼贴图案似乎组成了某种地图。仔细查看那些彩色的碎片是否指向某个位置。",
                "explore_x": 12,
                "explore_y": 10,
            }
        },
        {
            "action": {
                "action_type": "combat",
                "target_id": "orc_boss",
                "target_type": "actor",
                "thought": "水中突然伸出无数触手——封印里的东西正在苏醒。必须在它完全挣脱前压制住它！",
            }
        },
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
    "azure_town": DATASET_AZURE_TOWN,
    "taba_town": DATASET_TABA_TOWN,
    "tunnel": DATASET_TUNNEL,
    "cathedral": DATASET_CATHEDRAL,
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
    """获取某个 purpose 的 mock 数据——优先数据集内，回退到跨数据集 pool."""
    ds = get_dataset(dataset_name)
    pool = ds.get(purpose, [])
    if not pool:
        pool = _POOL.get(purpose, [])
    return random.choice(pool) if pool else {}
