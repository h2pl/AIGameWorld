--  ============================================================
--  AIGameWorld SQLite Schema / 数据库表结构定义
--  15 张表：实体 + 故事 + 关系 + 日志 / 15 tables: entities + stories + relations + logs
--  WAL 模式：支持并发读 + 单写 / WAL mode: concurrent reads + single write
--  ============================================================

PRAGMA journal_mode=WAL;    -- 预写日志模式 / Write-Ahead Log mode
PRAGMA foreign_keys=ON;     -- 外键约束 / Foreign key constraints

-- ============================================================
--  schema_version: 数据库版本追踪 / Database version tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,                    -- 版本号 / Version number
    applied_at  TEXT NOT NULL DEFAULT (datetime('now')) -- 应用时间 / Applied timestamp
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

-- ============================================================
--  world_meta: 世界元数据（单行 key-value）/ World metadata (key-value store)
-- ============================================================
CREATE TABLE IF NOT EXISTS world_meta (
    key   TEXT PRIMARY KEY,     -- 键：current_tick/current_scene/world_config / Key
    value TEXT NOT NULL         -- 值（JSON 编码的字符串）/ Value (JSON-encoded)
);

-- ============================================================
--  player_characters: 主角团 / Main cast (Player Characters)
--  4 个 PC：战士/盗贼/牧师/法师 / 4 PCs: fighter/rogue/cleric/wizard
-- ============================================================
CREATE TABLE IF NOT EXISTS player_characters (
    -- Basic Info / 基本信息 --
    id                  TEXT PRIMARY KEY,                       -- pc_fighter/pc_rogue 等
    name                TEXT NOT NULL,                          -- 角色名 / Character name
    role                TEXT NOT NULL,                          -- 职业：fighter/rogue/cleric/wizard
    race                TEXT,                                   -- 种族 / Race (e.g. human/dwarf/elf)
    status              TEXT NOT NULL DEFAULT 'active',         -- active/dead/left
    scene_id            TEXT NOT NULL,                          -- 所在场景 / Current scene
    position_x          INTEGER NOT NULL DEFAULT 0,             -- X 坐标 / X coordinate
    position_y          INTEGER NOT NULL DEFAULT 0,             -- Y 坐标 / Y coordinate

    -- Attributes & Combat / 属性与战斗 --
    attributes_json     TEXT NOT NULL,                          -- {str,dex,con,int,wis,cha}
    combat_json         TEXT NOT NULL,                          -- {hp,max_hp,ac,initiative,attack_bonus,damage_bonus}

    -- Character Arc / 角色弧 --
    character_arc_json  TEXT NOT NULL,                          -- {growth_line,inner_conflict,destiny}
    long_term_goal      TEXT,                                   -- 长期目标 / Long-term goal
    values_json         TEXT NOT NULL DEFAULT '[]',             -- 价值观列表 / Core values
    personality         TEXT,                                   -- 性格描述 / Personality description

    -- Inventory & Equipment / 背包与装备 --
    equipment_json      TEXT NOT NULL DEFAULT '{}',             -- {weapon,off_hand,armor,accessories:[]}
    inventory_json      TEXT NOT NULL DEFAULT '[]',             -- [{item_id,qty}]

    -- Memory System / 记忆系统 --
    memory_count            INTEGER NOT NULL DEFAULT 0,         -- 记忆条数 / Memory entry count
    importance_accumulator  REAL NOT NULL DEFAULT 0,            -- 重要性累计 / Importance accumulator
    reflection_threshold    INTEGER NOT NULL DEFAULT 100,       -- 反思阈值 / Reflection trigger threshold
    relationships_json      TEXT NOT NULL DEFAULT '{}',         -- {target_id: {attitude,history}}

    -- Roster / 花名册 --
    joined_tick     INTEGER NOT NULL DEFAULT 0,                 -- 加入时的 tick
    roster_status   TEXT NOT NULL DEFAULT 'member',             -- member/departed

    -- Timestamps / 时间戳 --
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  actors: 配角/Actor / Supporting characters (Actors)
--  商人/守卫/敌人/Boss/路人等 / merchant/guard/enemy/boss/bystander
-- ============================================================
CREATE TABLE IF NOT EXISTS actors (
    -- Basic Info / 基本信息 --
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT,                                   -- 角色描述 / Role description
    race        TEXT,
    status      TEXT NOT NULL DEFAULT 'active',         -- active/dead/inactive
    scene_id    TEXT NOT NULL,
    position_x  INTEGER NOT NULL DEFAULT 0,
    position_y  INTEGER NOT NULL DEFAULT 0,

    -- Attributes & Combat / 属性与战斗 --
    attributes_json TEXT NOT NULL,
    combat_json     TEXT,                               -- 路人可为空 / Nullable for bystanders

    -- Personality & Functions / 性格与功能 --
    personality         TEXT,
    functions_json      TEXT NOT NULL DEFAULT '[]',     -- ["merchant","dialogue","enemy"]
    function_data_json  TEXT NOT NULL DEFAULT '{}',     -- 按 function 存扩展数据 / Extended data per function

    -- Inventory & Equipment / 背包与装备 --
    equipment_json  TEXT,                               -- 可为空 / Nullable
    inventory_json  TEXT NOT NULL DEFAULT '[]',

    -- Memory System / 记忆系统 --
    memory_count            INTEGER NOT NULL DEFAULT 0,
    importance_accumulator  REAL NOT NULL DEFAULT 0,
    reflection_threshold    INTEGER NOT NULL DEFAULT 200,   -- Actor 反思阈值更高 / Higher threshold
    relationships_json      TEXT NOT NULL DEFAULT '{}',

    -- DM Control / DM 控制 --
    dm_assigned         INTEGER NOT NULL DEFAULT 0,         -- DM 本步是否指定出场 / DM-assigned for this tick
    motivation_injected TEXT,                               -- DM 注入的动机 / DM-injected motivation
    service_arcs_json   TEXT NOT NULL DEFAULT '[]',         -- 服务于哪些 StoryArc

    -- Timestamps / 时间戳 --
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  main_cast: 主角团花名册变更历史 / Main cast roster change history
-- ============================================================
CREATE TABLE IF NOT EXISTS main_cast (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tick            INTEGER NOT NULL,                       -- 变更发生的 tick
    character_id    TEXT NOT NULL,                          -- pc_id
    event_type      TEXT NOT NULL,                          -- join/leave/death/betrayal
    reason          TEXT,                                   -- 原因 / Reason
    arc_id          TEXT,                                   -- 关联剧情线 / Related story arc
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  scenes: 场景定义 / Scene definitions
-- ============================================================
CREATE TABLE IF NOT EXISTS scenes (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,                          -- 场景名 / Scene name
    type            TEXT NOT NULL,                          -- outdoor/indoor/underground
    description     TEXT,                                   -- 场景描述 / Description
    exits_json      TEXT NOT NULL DEFAULT '[]',             -- [{direction,target_scene}] 出口
    landmarks_json  TEXT NOT NULL DEFAULT '[]',             -- [{id,name,position}] 地标
    environment_json TEXT NOT NULL DEFAULT '{}',            -- {weather,time_of_day} 环境
    pack_id         TEXT NOT NULL,                          -- 所属 Pack ID（关联键）/ Source pack ID (FK key)
    pack_name       TEXT NOT NULL                           -- 所属 Pack 名称 / Source pack name
);

-- ============================================================
--  items: 物品全局定义 / Global item definitions
-- ============================================================
CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,                              -- 物品名 / Item name
    item_type   TEXT NOT NULL,                              -- weapon/armor/shield/potion/scroll/key/consumable/misc
    rarity      TEXT NOT NULL DEFAULT 'common',             -- common/uncommon/rare/legendary/artifact
    weight      REAL NOT NULL DEFAULT 0,                    -- 重量 / Weight
    value       INTEGER NOT NULL DEFAULT 0,                 -- 基础价格（金币）/ Base value (gold)
    description TEXT,                                       -- 描述 / Description
    data_json   TEXT NOT NULL DEFAULT '{}',                 -- 按 type 存不同结构 / Type-specific data
    pack_id     TEXT NOT NULL,                              -- 所属 Pack ID（关联键）/ Source pack ID (FK key)
    pack_name   TEXT NOT NULL                               -- 所属 Pack 名称 / Source pack name
);

-- ============================================================
--  scene_objects: 场景对象 / Scene objects (non-autonomous entities)
--  宝箱/门/陷阱/机关/动物/掉落物 / container/door/trap/mechanism/animal/item_drop
-- ============================================================
CREATE TABLE IF NOT EXISTS scene_objects (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    object_type         TEXT NOT NULL,                      -- container/door/trap/animal/mechanism/decoration/item_drop
    scene_id            TEXT NOT NULL,                      -- 所在场景 / Parent scene
    position_x          INTEGER NOT NULL DEFAULT 0,
    position_y          INTEGER NOT NULL DEFAULT 0,
    interactable        INTEGER NOT NULL DEFAULT 1,         -- 是否可交互 / Interactable
    interact_data_json  TEXT,                               -- {locked,lock_dc,items,leads_to,...}
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (scene_id) REFERENCES scenes(id)
);
CREATE INDEX IF NOT EXISTS idx_scene_objects_scene ON scene_objects(scene_id);

-- ============================================================
--  story_arcs: 剧情线 / Story arcs
-- ============================================================
CREATE TABLE IF NOT EXISTS story_arcs (
    id                      TEXT PRIMARY KEY,
    type                    TEXT NOT NULL,                  -- main/side
    title                   TEXT NOT NULL,                  -- 剧情线标题 / Arc title
    stage                   TEXT,                           -- 铺陈/发展/冲突升级/高潮/收尾
    main_cast_json          TEXT NOT NULL DEFAULT '[]',     -- 涉及的主角团 / Involved PCs
    supporting_actors_json  TEXT NOT NULL DEFAULT '[]',     -- 涉及的配角 / Involved actors
    key_event_ticks_json    TEXT NOT NULL DEFAULT '[]',     -- 关键事件 tick / Key event ticks
    branching_points_json   TEXT NOT NULL DEFAULT '[]',     -- 分支点记录 / Branching points
    status                  TEXT NOT NULL DEFAULT 'setup'   -- setup/active/climax/resolved/abandoned
);

-- ============================================================
--  story_hooks: 伏笔 / Story hooks (foreshadowing)
-- ============================================================
CREATE TABLE IF NOT EXISTS story_hooks (
    id              TEXT PRIMARY KEY,
    planted_tick    INTEGER NOT NULL,                       -- 埋下伏笔的 tick
    description     TEXT NOT NULL,                          -- 伏笔描述 / Hook description
    intended_payoff TEXT,                                   -- 预期回收方式 / Intended payoff
    urgency         INTEGER,                                -- 紧迫度（多久内回收）/ Urgency
    status          TEXT NOT NULL DEFAULT 'planted'         -- planted/escalated/paid_off/abandoned
);

-- ============================================================
--  events: 事件日志（只追加）/ Event log (append-only)
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,                           -- evt_{tick}_{seq}
    tick        INTEGER NOT NULL,                           -- 发生的 tick
    seq         INTEGER NOT NULL,                           -- 同一 tick 内的序号 / Sequence within tick
    type        TEXT NOT NULL,                              -- 事件类型 / Event type
    importance  INTEGER NOT NULL DEFAULT 1,                 -- 重要性评分(0-10) / Importance score
    source      TEXT,                                       -- 来源：pc_id/actor_id/dm / Source
    target      TEXT,                                       -- 目标：pc_id/actor_id/scene_object_id / Target
    data_json   TEXT NOT NULL,                              -- 事件详情 / Event data
    narrative   TEXT,                                       -- 叙事文本 / Narrative text
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);

-- ============================================================
--  narratives: 叙事日志 / Narrative log
-- ============================================================
CREATE TABLE IF NOT EXISTS narratives (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tick        INTEGER NOT NULL,
    content     TEXT NOT NULL,                              -- 叙事文本 / Narrative text
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_narratives_tick ON narratives(tick);

-- ============================================================
--  quests: 任务 / Quests
-- ============================================================
CREATE TABLE IF NOT EXISTS quests (
    id              TEXT PRIMARY KEY,
    arc_id          TEXT,                                   -- 关联剧情线 / Related story arc
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'inactive',       -- inactive/active/completed/failed
    progress_json   TEXT NOT NULL DEFAULT '{}',             -- 任务进度 / Progress
    assigned_pcs_json TEXT NOT NULL DEFAULT '[]',           -- 接取者 / Assigned PCs
    created_tick    INTEGER,                                -- 创建时的 tick
    completed_tick  INTEGER                                 -- 完成时的 tick
);

-- ============================================================
--  factions: 势力 / Factions
-- ============================================================
CREATE TABLE IF NOT EXISTS factions (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    leader_character_id TEXT,                               -- 势力首领 / Faction leader
    influence           REAL NOT NULL DEFAULT 0.5,          -- 影响力(0-1) / Influence
    members_json        TEXT NOT NULL DEFAULT '[]',         -- 成员列表 / Member list
    allies_json         TEXT NOT NULL DEFAULT '[]',         -- 盟友列表 / Ally list
    enemies_json        TEXT NOT NULL DEFAULT '[]'          -- 敌对列表 / Enemy list
);
