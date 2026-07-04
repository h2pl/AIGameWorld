--  ============================================================
--  AIGameWorld SQLite Schema / 数据库表结构定义
--  WAL 模式：支持并发读 + 单写 / WAL mode: concurrent reads + single write
--  ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================
--  worlds: 世界 / Worlds
-- ============================================================
CREATE TABLE IF NOT EXISTS worlds (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    version         TEXT NOT NULL DEFAULT '1.0.0',
    rule_set        TEXT NOT NULL DEFAULT 'dnd_5e_srd',
    author          TEXT NOT NULL DEFAULT '',
    starting_scene  TEXT NOT NULL DEFAULT '',
    current_tick    INTEGER NOT NULL DEFAULT 0,
    ext_json        TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  player_characters: 主角团 / Player Characters
-- ============================================================
CREATE TABLE IF NOT EXISTS player_characters (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    role                TEXT NOT NULL,
    race                TEXT,
    status              TEXT NOT NULL DEFAULT 'active',
    scene_id            TEXT NOT NULL,
    position_x          INTEGER NOT NULL DEFAULT 0,
    position_y          INTEGER NOT NULL DEFAULT 0,
    attributes_json     TEXT NOT NULL,
    combat_json         TEXT NOT NULL,
    arc_json            TEXT NOT NULL,
    long_term_goal      TEXT,
    values_json         TEXT NOT NULL DEFAULT '[]',
    personality         TEXT,
    equipment_json      TEXT NOT NULL DEFAULT '{}',
    inventory_json      TEXT NOT NULL DEFAULT '[]',
    memory_count            INTEGER NOT NULL DEFAULT 0,
    importance_accumulator  REAL NOT NULL DEFAULT 0,
    relationships_json      TEXT NOT NULL DEFAULT '{}',
    joined_tick         INTEGER NOT NULL DEFAULT 0,
    roster_status       TEXT NOT NULL DEFAULT 'member',
    world_id            TEXT NOT NULL DEFAULT '',
    ext_json            TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  actors: 配角 / Actors
-- ============================================================
CREATE TABLE IF NOT EXISTS actors (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT,
    race        TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    disposition TEXT NOT NULL DEFAULT 'neutral',
    scene_id    TEXT NOT NULL,
    position_x  INTEGER NOT NULL DEFAULT 0,
    position_y  INTEGER NOT NULL DEFAULT 0,
    attributes_json TEXT NOT NULL,
    combat_json     TEXT,
    personality         TEXT,
    functions_json      TEXT NOT NULL DEFAULT '[]',
    function_data_json  TEXT NOT NULL DEFAULT '{}',
    equipment_json  TEXT,
    inventory_json  TEXT NOT NULL DEFAULT '[]',
    memory_count            INTEGER NOT NULL DEFAULT 0,
    importance_accumulator  REAL NOT NULL DEFAULT 0,
    relationships_json      TEXT NOT NULL DEFAULT '{}',
    dm_assigned         INTEGER NOT NULL DEFAULT 0,
    motivation_injected TEXT,
    world_id            TEXT NOT NULL DEFAULT '',
    ext_json            TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  scenes: 场景定义 / Scene definitions
-- ============================================================
CREATE TABLE IF NOT EXISTS scenes (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,
    description     TEXT,
    world_id        TEXT NOT NULL,
    ext_json        TEXT NOT NULL DEFAULT '{}',
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
    data        TEXT NOT NULL DEFAULT '{}',
    world_id    TEXT NOT NULL,
    ext_json    TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  scene_objects: 场景物体 / Scene objects
-- ============================================================
CREATE TABLE IF NOT EXISTS scene_objects (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    object_type         TEXT NOT NULL,
    scene_id            TEXT NOT NULL,
    position_x          INTEGER NOT NULL DEFAULT 0,
    position_y          INTEGER NOT NULL DEFAULT 0,
    interactable        INTEGER NOT NULL DEFAULT 1,
    interact_data       TEXT,
    world_id            TEXT NOT NULL DEFAULT '',
    ext_json            TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (scene_id) REFERENCES scenes(id)
);
CREATE INDEX IF NOT EXISTS idx_scene_objects_scene ON scene_objects(scene_id);


-- ============================================================
--  tick_messages: 消息元数据 / Message metadata
-- ============================================================
CREATE TABLE IF NOT EXISTS tick_messages (
    id          TEXT    NOT NULL,
    tick        INTEGER NOT NULL,
    world_id    TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'building',
    is_last     INTEGER NOT NULL DEFAULT 0,
    ext_json    TEXT    NOT NULL DEFAULT '{}',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    acked_at    TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tick_message_id_tick ON tick_messages(id, tick);
CREATE INDEX IF NOT EXISTS idx_msg_status ON tick_messages(id, status);
CREATE INDEX IF NOT EXISTS idx_msg_world ON tick_messages(world_id);

-- ============================================================
--  tick_events: 消息事件明细 / Message event details
-- ============================================================
CREATE TABLE IF NOT EXISTS tick_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_message_id TEXT    NOT NULL,
    tick            INTEGER NOT NULL,
    type            TEXT    NOT NULL,
    payload         TEXT    NOT NULL,
    world_id        TEXT    NOT NULL DEFAULT '',
    ext_json        TEXT    NOT NULL DEFAULT '{}',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (tick_message_id, tick) REFERENCES tick_messages(id, tick)
);
CREATE INDEX IF NOT EXISTS idx_tick_events_msg ON tick_events(tick_message_id, tick);
CREATE INDEX IF NOT EXISTS idx_tick_events_world_tick ON tick_events(world_id, tick);



-- ============================================================
--  dm_records: DM 产出记录 / DM output records
-- ============================================================
CREATE TABLE IF NOT EXISTS dm_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id        TEXT NOT NULL,
    tick            INTEGER NOT NULL,
    plot_brief      TEXT NOT NULL DEFAULT '',
    hint_list       TEXT NOT NULL DEFAULT '[]',
    dm_narrative    TEXT NOT NULL DEFAULT '',
    ext_json        TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, tick)
);
CREATE INDEX IF NOT EXISTS idx_dm_records_world_tick ON dm_records(world_id, tick);

-- ============================================================
--  story_summaries: 故事摘要 / Story summaries
-- ============================================================
CREATE TABLE IF NOT EXISTS story_summaries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id        TEXT NOT NULL,
    tick_start      INTEGER NOT NULL,
    tick_end        INTEGER NOT NULL,
    summary         TEXT NOT NULL,
    ext_json        TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(world_id, tick_start)
);
CREATE INDEX IF NOT EXISTS idx_summaries_world ON story_summaries(world_id);
