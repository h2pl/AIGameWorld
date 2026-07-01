--  ============================================================
--  AIGameWorld SQLite Schema / 数据库表结构定义
--  WAL 模式：支持并发读 + 单写 / WAL mode: concurrent reads + single write
--  ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================
--  worlds: 世界 / Worlds——承载 world_pack 元信息 + 运行时状态
-- ============================================================
CREATE TABLE IF NOT EXISTS worlds (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    version         TEXT NOT NULL DEFAULT '1.0.0',
    rule_set        TEXT NOT NULL DEFAULT 'dnd_5e_srd',
    author          TEXT NOT NULL DEFAULT '',
    starting_scene  TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
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

    -- Pack / world 标识 --
    world_id         TEXT NOT NULL DEFAULT '',                   -- world 标识 ID（关联键）/ world 标识 ID (FK key)

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

    -- Pack / world 标识 --
    world_id             TEXT NOT NULL DEFAULT '',            -- world 标识 ID（关联键）/ world 标识 ID (FK key)

    -- Timestamps / 时间戳 --
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  scenes: 场景定义 / Scene definitions
-- ============================================================
CREATE TABLE IF NOT EXISTS scenes (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,                          -- outdoor/indoor/underground
    description     TEXT,
    exits_json      TEXT NOT NULL DEFAULT '[]',
    landmarks_json  TEXT NOT NULL DEFAULT '[]',
    environment_json TEXT NOT NULL DEFAULT '{}',
    world_id         TEXT NOT NULL,
    world_name       TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  items: 物品全局定义 / Global item definitions
-- ============================================================
CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    item_type   TEXT NOT NULL,
    rarity      TEXT NOT NULL DEFAULT 'common',
    weight      REAL NOT NULL DEFAULT 0,
    value       INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    data_json   TEXT NOT NULL DEFAULT '{}',
    world_id     TEXT NOT NULL,
    world_name   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  scene_objects: 场景对象 / Scene objects (non-autonomous entities)
--  宝箱/门/陷阱/机关/动物/掉落物 / container/door/trap/mechanism/animal/item_drop
-- ============================================================
CREATE TABLE IF NOT EXISTS scene_objects (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    object_type         TEXT NOT NULL,
    scene_id            TEXT NOT NULL,
    position_x          INTEGER NOT NULL DEFAULT 0,
    position_y          INTEGER NOT NULL DEFAULT 0,
    interactable        INTEGER NOT NULL DEFAULT 1,
    interact_data_json  TEXT,
    world_id             TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (scene_id) REFERENCES scenes(id)
);
CREATE INDEX IF NOT EXISTS idx_scene_objects_scene ON scene_objects(scene_id);



-- ============================================================
--  messages: 消息元数据 / Message metadata
--  Graph 生产 → 写入 DB → 前端轮询读取 → ACK 标记已消费
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id         TEXT    NOT NULL,                               -- 消息标识 / Message identifier
    tick       INTEGER NOT NULL,                               -- tick 序号 / Tick number
    world_id   TEXT    NOT NULL,                               -- FK → worlds.id
    status     TEXT    NOT NULL DEFAULT 'pending',             -- pending | consumed
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now')),
    acked_at   TEXT                                            -- ACK 时间
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_id_tick ON messages(id, tick);
CREATE INDEX IF NOT EXISTS idx_msg_status ON messages(id, status);
CREATE INDEX IF NOT EXISTS idx_msg_world ON messages(world_id);

-- ============================================================
--  events: 消息事件明细 / Message event details
--  一条消息包含多个事件，按 id（自增=入库顺序）排序
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_id      TEXT    NOT NULL,                               -- FK → messages.id
    msg_tick    INTEGER NOT NULL,                               -- FK → messages.tick
    type        TEXT    NOT NULL,                               -- 7 种事件类型
    payload     TEXT    NOT NULL,                               -- 事件 JSON（不含 type）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (msg_id, msg_tick) REFERENCES messages(id, tick)
);
CREATE INDEX IF NOT EXISTS idx_events_msg ON events(msg_id, msg_tick);

-- ============================================================
--  dm_records: DM 产出记录 / DM output records——每 tick 一行
-- ============================================================
CREATE TABLE IF NOT EXISTS dm_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id        TEXT NOT NULL,
    tick            INTEGER NOT NULL,
    plot_brief      TEXT NOT NULL DEFAULT '',
    hint_list      TEXT NOT NULL DEFAULT '[]',
    dm_narrative    TEXT NOT NULL DEFAULT '',
    ext_json        TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, tick)
);
CREATE INDEX IF NOT EXISTS idx_dm_records_world_tick ON dm_records(world_id, tick);

-- ============================================================
--  story_summaries: 故事摘要 / Story summaries——每 N tick LLM 压缩
-- ============================================================
CREATE TABLE IF NOT EXISTS story_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id        TEXT NOT NULL,
    tick_start      INTEGER NOT NULL,
    tick_end        INTEGER NOT NULL,
    summary         TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, tick_start)
);
CREATE INDEX IF NOT EXISTS idx_summaries_world ON story_summaries(world_id);

-- ============================================================
--  quests: 任务 / Quests
-- ============================================================
CREATE TABLE IF NOT EXISTS quests (
    id              TEXT PRIMARY KEY,
    arc_id          TEXT,
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'inactive',
    progress_json   TEXT NOT NULL DEFAULT '{}',
    assigned_pcs_json TEXT NOT NULL DEFAULT '[]',
    created_tick    INTEGER,
    completed_tick  INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);


