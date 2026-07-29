"""给 ChromaDB 灌入一批真实向量数据（用于 chromadb-admin 可视化演示）.

不调用外部 LLM API，纯本地：
1. 使用项目的 ChromaClient.create_with_bge_m3() → BGE-M3 真实嵌入
2. 严格遵循 memory_repo.py / knowledge_repo.py 中的集合命名与字段规范
3. 写入角色长期记忆、反思记忆、世界包知识库（场景/NPC/任务/地点/派系）等共 6+ collections
"""

import os
import sys
import time
from pathlib import Path
from uuid import uuid4

# 把 backend 加入 import path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from src.storage.chroma_client import ChromaClient

PERSIST_PATH = backend_dir / "data" / "chroma"
PERSIST_PATH.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# 1. 演示数据（贴近世界观叙事）
# ─────────────────────────────────────────────────────────────
WORLD_ID = "world_demo_01"
PACK_NAME = "demo_pack"

# —— 主角：李星河 ——
PC_ID = "lixinghe"

MEMORIES = [
    # (content, tick, importance, type, period, entity_type)
    (
        "第3天黄昏，我在迷雾森林边缘救下了重伤的小鹿，将其带回药庐照料。",
        3,
        3,
        "observation",
        "long_term",
        "pc",
    ),
    (
        "在与猎户老张的对话中得知，最近村庄接连失踪的人都与后山的黑风寨有关。",
        5,
        6,
        "dialog",
        "long_term",
        "pc",
    ),
    (
        "第7天夜晚，我在梦中听到一个古老声音呼唤我的名字，指引我前往卧龙谷。",
        7,
        7,
        "reflection",
        "long_term",
        "pc",
    ),
    (
        "我与剑派大弟子比试剑法，连输三局，意识到自己的内力仍需苦修。",
        12,
        4,
        "action",
        "medium_term",
        "pc",
    ),
    (
        "白长老私下对我说：你的身世并非表面那样简单，切记不要信任任何人。",
        15,
        9,
        "dialog",
        "long_term",
        "pc",
    ),
    (
        "在藏经阁第三层找到一本残缺的《青云心法》，似乎与我修炼的功法同源。",
        18,
        8,
        "observation",
        "long_term",
        "pc",
    ),
    (
        "小师妹苏晴偷偷塞给我一瓶疗伤丹药，并嘱咐我莫要让其他弟子看见。",
        21,
        5,
        "dialog",
        "medium_term",
        "pc",
    ),
    (
        "后山山洞中发现一副古老壁画，画上的人物与我左肩上的胎记极为相似。",
        25,
        8,
        "observation",
        "long_term",
        "pc",
    ),
]

REFLECTIONS = [
    # (insight, tick)
    ("黑风寨最近的异常活动绝非简单的劫掠，背后必有更大的势力支持。", 10),
    ("梦中的声音与卧龙谷之间存在某种联系，这很可能是解开我身世之谜的钥匙。", 20),
    ("白长老的话值得深思，门派内部可能存在不为人知的对立派系，我需明哲保身。", 28),
]

# —— 知识库里的地点/NPC/任务 ——
KNOWLEDGE_LOCATIONS = [
    {"name": "迷雾森林", "desc": "位于村庄西侧，常年被浓雾笼罩，传说林中栖息着古老的灵兽。"},
    {
        "name": "卧龙谷",
        "desc": "山脉深处的隐秘山谷，古籍记载为上古仙人的修炼道场，入口已被封印千年。",
    },
    {"name": "青云宗", "desc": "正道第一宗门，占地百里，分九峰十八院，以御剑之术闻名天下。"},
    {"name": "黑风寨", "desc": "盘踞后山的山贼据点，近年实力暴涨，似乎与魔道有所勾结。"},
]

KNOWLEDGE_NPCS = [
    {"name": "白长老", "desc": "青云宗执法堂长老，表面刚正不阿，实则心机深沉，与掌门暗中角力。"},
    {"name": "苏晴", "desc": "青云宗小师妹，天赋异禀，性格活泼开朗，对主角怀有好感。"},
    {
        "name": "猎户老张",
        "desc": "村庄里年过六旬的老猎户，熟悉山林地形，消息灵通，表面普通实则藏有往事。",
    },
    {"name": "剑派大弟子陈风", "desc": "青云宗首席弟子，剑法出众，为人傲慢，对主角抱有敌意。"},
]

KNOWLEDGE_QUESTS = [
    {
        "title": "调查失踪案",
        "desc": "受村长所托，调查村庄连续失踪案，线索指向黑风寨，需在月圆之夜潜入。",
    },
    {
        "title": "寻找灵兽踪迹",
        "desc": "白长老交付的秘密任务：寻找传说中的九尾灵狐，据说能指引人前往卧龙谷。",
    },
    {"title": "破解壁画之谜", "desc": "解读后山山洞壁画的含义，找出与胎记相似人物的真实身份。"},
]

KNOWLEDGE_FACTIONS = [
    {"name": "青云宗", "desc": "正道领袖，主张除魔卫道，但内部派系林立，权力斗争激烈。"},
    {"name": "黑风寨", "desc": "表面山贼，实为魔道外围组织，听命于神秘的'主上'。"},
    {"name": "隐世医谷", "desc": "中立派势力，精通医术与毒药，甚少涉足江湖纷争。"},
]

KNOWLEDGE_LORE = [
    {
        "title": "青云心法传说",
        "content": "相传青云心法由上古仙人所创，共分九层。练至第七层便可御剑飞行，第九层据说能破碎虚空。但自开派祖师之后，再无人突破第八层。",
    },
    {
        "title": "九尾灵狐传说",
        "content": "九尾灵狐是上古灵兽，每百年生一尾，九尾成形便有化人之能。传说其眼中藏有通往仙界的钥匙，引得无数修士前仆后继。",
    },
]

SCENES = [
    {
        "id": "scene_village_day",
        "content": "夕阳下的村庄：炊烟袅袅，孩童嬉闹，老人们坐在村口的大槐树下闲谈。远处的田埂上，几个农妇正弯腰劳作。气氛宁静祥和。",
    },
    {
        "id": "scene_forest_night",
        "content": "月夜迷雾森林：薄雾如纱，月光透过稀疏的枝叶洒在斑驳的地面。远处传来几声夜枭的啼叫，草丛中偶尔闪过一双发亮的兽瞳。神秘而压抑。",
    },
    {
        "id": "scene_sword_hall",
        "content": "青云宗剑术演武堂：宽敞的青石大厅中央，十八般武器整齐陈列。四周墙上挂着历代掌门的画像，地面刻有复杂的剑法阵图。空气里弥漫着淡淡的檀香。",
    },
]


# ─────────────────────────────────────────────────────────────
# 2. 写入引擎
# ─────────────────────────────────────────────────────────────
def memory_meta(tick, importance, type_, period, entity_type, world_id=WORLD_ID) -> dict:
    return {
        "tick": tick,
        "importance": importance,
        "type": type_,
        "period": period,
        "entity_type": entity_type,
        "world_id": world_id,
    }


def knowledge_meta(pack: str, type_: str, source: str, extra: dict | None = None) -> dict:
    m = {"pack": pack, "type": type_, "source": source}
    if extra:
        m.update(extra)
    return m


def seed(c: ChromaClient) -> dict:
    """写入真实向量数据，返回统计摘要。"""
    stats: dict[str, int] = {}

    t0 = time.time()

    # —— 角色长期记忆 mem_{pc_id} ——
    col_mem = f"mem_{PC_ID}"
    ids_m, docs_m, metas_m = [], [], []
    for i, (content, tick, imp, t, p, e) in enumerate(MEMORIES):
        mem_id = f"mem_{PC_ID}_{tick}_{uuid4().hex[:6]}"
        ids_m.append(mem_id)
        docs_m.append(content)
        metas_m.append(memory_meta(tick, imp, t, p, e))
    c.add(col_mem, ids=ids_m, documents=docs_m, metadatas=metas_m)
    stats[col_mem] = len(ids_m)

    # —— 角色反思记忆 reflect_{pc_id} ——
    col_ref = f"reflect_{PC_ID}"
    ids_r, docs_r, metas_r = [], [], []
    for i, (insight, tick) in enumerate(REFLECTIONS):
        ref_id = f"reflect_{PC_ID}_{tick}_{uuid4().hex[:6]}"
        ids_r.append(ref_id)
        docs_r.append(insight)
        meta = memory_meta(tick, 10, "reflection", "long_term", "pc")
        meta["id"] = ref_id
        metas_r.append(meta)
    c.add(col_ref, ids=ids_r, documents=docs_r, metadatas=metas_r)
    stats[col_ref] = len(ids_r)

    # —— 世界包知识库：地点 ——
    col_loc = f"knowledge_{PACK_NAME}_locations"
    ids_l, docs_l, metas_l = [], [], []
    for i, item in enumerate(KNOWLEDGE_LOCATIONS):
        ids_l.append(f"{PACK_NAME}_locations_{i}")
        docs_l.append(f"{item['name']}: {item['desc']}")
        metas_l.append(
            knowledge_meta(
                PACK_NAME, "locations", "seed_data.yaml", {"name": item["name"], "index": i}
            )
        )
    c.add(col_loc, ids=ids_l, documents=docs_l, metadatas=metas_l)
    stats[col_loc] = len(ids_l)

    # —— 世界包知识库：NPC ——
    col_npc = f"knowledge_{PACK_NAME}_npcs"
    ids_n, docs_n, metas_n = [], [], []
    for i, item in enumerate(KNOWLEDGE_NPCS):
        ids_n.append(f"{PACK_NAME}_npcs_{i}")
        docs_n.append(f"{item['name']}: {item['desc']}")
        metas_n.append(
            knowledge_meta(PACK_NAME, "npcs", "seed_data.yaml", {"name": item["name"], "index": i})
        )
    c.add(col_npc, ids=ids_n, documents=docs_n, metadatas=metas_n)
    stats[col_npc] = len(ids_n)

    # —— 世界包知识库：任务 ——
    col_q = f"knowledge_{PACK_NAME}_quests"
    ids_q, docs_q, metas_q = [], [], []
    for i, item in enumerate(KNOWLEDGE_QUESTS):
        ids_q.append(f"{PACK_NAME}_quests_{i}")
        docs_q.append(f"{item['title']}: {item['desc']}")
        metas_q.append(
            knowledge_meta(
                PACK_NAME, "quests", "seed_data.yaml", {"title": item["title"], "index": i}
            )
        )
    c.add(col_q, ids=ids_q, documents=docs_q, metadatas=metas_q)
    stats[col_q] = len(ids_q)

    # —— 世界包知识库：派系 ——
    col_f = f"knowledge_{PACK_NAME}_factions"
    ids_f, docs_f, metas_f = [], [], []
    for i, item in enumerate(KNOWLEDGE_FACTIONS):
        ids_f.append(f"{PACK_NAME}_factions_{i}")
        docs_f.append(f"{item['name']}: {item['desc']}")
        metas_f.append(
            knowledge_meta(
                PACK_NAME, "factions", "seed_data.yaml", {"name": item["name"], "index": i}
            )
        )
    c.add(col_f, ids=ids_f, documents=docs_f, metadatas=metas_f)
    stats[col_f] = len(ids_f)

    # —— 世界包知识库：传说 ——
    col_lore = f"knowledge_{PACK_NAME}_lore"
    ids_lo, docs_lo, metas_lo = [], [], []
    for i, item in enumerate(KNOWLEDGE_LORE):
        ids_lo.append(f"{PACK_NAME}_lore_{i}")
        docs_lo.append(f"{item['title']}: {item['content']}")
        metas_lo.append(
            knowledge_meta(
                PACK_NAME, "lore", "seed_data.yaml", {"title": item["title"], "index": i}
            )
        )
    c.add(col_lore, ids=ids_lo, documents=docs_lo, metadatas=metas_lo)
    stats[col_lore] = len(ids_lo)

    # —— 场景 chunk scene_{world_id} ——
    col_scene = f"scene_{WORLD_ID}"
    ids_s, docs_s, metas_s = [], [], []
    for item in SCENES:
        ids_s.append(item["id"])
        docs_s.append(item["content"])
        metas_s.append({"world_id": WORLD_ID, "scene_id": item["id"], "source": "seed_data.yaml"})
    c.add(col_scene, ids=ids_s, documents=docs_s, metadatas=metas_s)
    stats[col_scene] = len(ids_s)

    dt = time.time() - t0

    # 最终统计
    print(f"\n✅ Seed 完成！共写入 {sum(stats.values())} 条文档，用时 {dt:.1f}s\n")
    print("Collection".ljust(42), "Count")
    print("-" * 56)
    for k, v in stats.items():
        print(f"  {k.ljust(40)} {v:>5d}")
    print("-" * 56)
    print(f"  TOTAL{'.' * 35} {sum(stats.values()):>5d}")

    return stats


def verify(c: ChromaClient, stats: dict) -> None:
    """语义检索演示：验证数据真实可用（BGE-M3 语义相似度）。"""
    print("\n🔍 语义检索验证（用 '我的身世' 查询 长期记忆）：")
    res = c.query(f"mem_{PC_ID}", "我的身世，左肩上的胎记是谁？", top_k=3)
    for r in res:
        print(
            f"  [{r['distance']:.3f}] {r['text'][:60]}... (tick={r['meta'].get('tick')}, imp={r['meta'].get('importance')})"
        )

    print("\n🔍 语义检索验证（用 '潜入查案' 查询 知识库任务）：")
    res2 = c.query(f"knowledge_{PACK_NAME}_quests", "潜入黑风寨查失踪案件", top_k=2)
    for r in res2:
        print(f"  [{r['distance']:.3f}] {r['text'][:80]}...")

    print("\n🔍 语义检索验证（用 '古老壁画' 查询 传说/知识库地点混合）：")
    res3 = c.query(f"knowledge_{PACK_NAME}_lore", "壁画上的人物是什么身份？", top_k=2)
    for r in res3:
        print(f"  [{r['distance']:.3f}] {r['text'][:80]}...")

    # 再做个跨 col 的元数据 check：直接用 Chroma 原生客户端 peeking
    raw = c._client.list_collections()
    print(f"\n📋 ChromaDB 原生 list_collections()：{[r.name for r in raw]}")
    for r in raw:
        col = c._client.get_collection(r.name)
        print(f"  · {r.name.ljust(40)} count={col.count()}, metadata={col.metadata}")


# ─────────────────────────────────────────────────────────────
def main() -> None:
    print(f"📁 Persist 目录: {PERSIST_PATH}")
    print("🔌 先删除旧的 demo 集合，保持演示数据干净...")

    # 先连一下清空老集合（避免重复）
    _tmp = ChromaClient.create_with_bge_m3(PERSIST_PATH)
    for pc_prefix in [f"mem_{PC_ID}", f"reflect_{PC_ID}"]:
        _tmp.delete_collection(pc_prefix)
    for kb in ["locations", "npcs", "quests", "factions", "lore"]:
        _tmp.delete_collection(f"knowledge_{PACK_NAME}_{kb}")
    _tmp.delete_collection(f"scene_{WORLD_ID}")
    del _tmp

    # 正式创建 + 写入（BGE-M3 会在第一次使用时下载模型，可能需要几十秒）
    print("⚙️  初始化 ChromaClient + BGE-M3 embedding (首次需下载 2.3GB 模型)...")
    client = ChromaClient.create_with_bge_m3(PERSIST_PATH)
    stats = seed(client)
    verify(client, stats)


if __name__ == "__main__":
    main()
