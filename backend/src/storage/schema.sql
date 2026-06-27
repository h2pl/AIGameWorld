-- SimGameWorld SQLite Schema
-- Based on docs/06-data-layer.md §4
-- WAL mode for concurrent reads + single write

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

-- World metadata (single-row key-value)
CREATE TABLE IF NOT EXISTS world_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Player characters (main cast)
CREATE TABLE IF NOT EXISTS player_characters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,                          -- fighter/rogue/cleric/wizard
    race TEXT,
    status TEXT NOT NULL DEFAULT 'active',       -- active/dead/left
    scene_id TEXT NOT NULL,
    position_x INTEGER NOT NULL DEFAULT 0,
    position_y INTEGER NOT NULL DEFAULT 0,
    attributes_json TEXT NOT NULL,               -- {str,dex,con,int,wis,cha}
    combat_json TEXT NOT NULL,                   -- {hp,max_hp,ac,initiative,attack_bonus,damage_bonus}
    character_arc_json TEXT NOT NULL,            -- {growth_line,inner_conflict,destiny}
    long_term_goal TEXT,
    values_json TEXT NOT NULL DEFAULT '[]',      -- ["Protect the weak","Justice above law"]
    personality TEXT,
    equipment_json TEXT NOT NULL DEFAULT '{}',   -- {weapon,off_hand,armor,accessories:[]}
    inventory_json TEXT NOT NULL DEFAULT '[]',   -- [{item_id,qty}]
    memory_count INTEGER NOT NULL DEFAULT 0,
    importance_accumulator REAL NOT NULL DEFAULT 0,
    reflection_threshold INTEGER NOT NULL DEFAULT 100,
    relationships_json TEXT NOT NULL DEFAULT '{}',
    joined_tick INTEGER NOT NULL DEFAULT 0,
    roster_status TEXT NOT NULL DEFAULT 'member', -- member/departed
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Actors (supporting characters)
CREATE TABLE IF NOT EXISTS actors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT,
    race TEXT,
    status TEXT NOT NULL DEFAULT 'active',       -- active/dead/inactive
    scene_id TEXT NOT NULL,
    position_x INTEGER NOT NULL DEFAULT 0,
    position_y INTEGER NOT NULL DEFAULT 0,
    attributes_json TEXT NOT NULL,
    combat_json TEXT,                            -- nullable for bystanders
    personality TEXT,
    functions_json TEXT NOT NULL DEFAULT '[]',   -- ["merchant","dialogue"]
    function_data_json TEXT NOT NULL DEFAULT '{}',
    equipment_json TEXT,                         -- nullable
    inventory_json TEXT NOT NULL DEFAULT '[]',
    memory_count INTEGER NOT NULL DEFAULT 0,
    importance_accumulator REAL NOT NULL DEFAULT 0,
    reflection_threshold INTEGER NOT NULL DEFAULT 200,
    relationships_json TEXT NOT NULL DEFAULT '{}',
    dm_assigned INTEGER NOT NULL DEFAULT 0,
    motivation_injected TEXT,
    service_arcs_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Main cast roster history
CREATE TABLE IF NOT EXISTS main_cast (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick INTEGER NOT NULL,
    character_id TEXT NOT NULL,
    event_type TEXT NOT NULL,                    -- join/leave/death/betrayal
    reason TEXT,
    arc_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Scenes
CREATE TABLE IF NOT EXISTS scenes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    exits_json TEXT NOT NULL DEFAULT '[]',
    landmarks_json TEXT NOT NULL DEFAULT '[]',
    environment_json TEXT NOT NULL DEFAULT '{}',
    pack_name TEXT NOT NULL
);

-- Global item definitions
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    item_type TEXT NOT NULL,                     -- weapon/armor/shield/potion/scroll/key/consumable/misc
    rarity TEXT NOT NULL DEFAULT 'common',
    weight REAL NOT NULL DEFAULT 0,
    value INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    data_json TEXT NOT NULL DEFAULT '{}',
    pack_name TEXT NOT NULL
);

-- Scene objects (non-autonomous entities)
CREATE TABLE IF NOT EXISTS scene_objects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    object_type TEXT NOT NULL,                   -- container/door/trap/animal/mechanism/decoration/item_drop
    scene_id TEXT NOT NULL,
    position_x INTEGER NOT NULL DEFAULT 0,
    position_y INTEGER NOT NULL DEFAULT 0,
    interactable INTEGER NOT NULL DEFAULT 1,
    interact_data_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (scene_id) REFERENCES scenes(id)
);
CREATE INDEX IF NOT EXISTS idx_scene_objects_scene ON scene_objects(scene_id);

-- Story arcs
CREATE TABLE IF NOT EXISTS story_arcs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,                          -- main/side
    title TEXT NOT NULL,
    stage TEXT,
    main_cast_json TEXT NOT NULL DEFAULT '[]',
    supporting_actors_json TEXT NOT NULL DEFAULT '[]',
    key_event_ticks_json TEXT NOT NULL DEFAULT '[]',
    branching_points_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'setup'
);

-- Story hooks (foreshadowing)
CREATE TABLE IF NOT EXISTS story_hooks (
    id TEXT PRIMARY KEY,
    planted_tick INTEGER NOT NULL,
    description TEXT NOT NULL,
    intended_payoff TEXT,
    urgency INTEGER,
    status TEXT NOT NULL DEFAULT 'planted'
);

-- Event log (append-only)
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,                         -- evt_{tick}_{seq}
    tick INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    type TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 1,
    source TEXT,
    target TEXT,
    data_json TEXT NOT NULL,
    narrative TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);

-- Narrative log
CREATE TABLE IF NOT EXISTS narratives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_narratives_tick ON narratives(tick);

-- Quests
CREATE TABLE IF NOT EXISTS quests (
    id TEXT PRIMARY KEY,
    arc_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'inactive',
    progress_json TEXT NOT NULL DEFAULT '{}',
    assigned_pcs_json TEXT NOT NULL DEFAULT '[]',
    created_tick INTEGER,
    completed_tick INTEGER
);

-- Factions
CREATE TABLE IF NOT EXISTS factions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    leader_character_id TEXT,
    influence REAL NOT NULL DEFAULT 0.5,
    members_json TEXT NOT NULL DEFAULT '[]',
    allies_json TEXT NOT NULL DEFAULT '[]',
    enemies_json TEXT NOT NULL DEFAULT '[]'
);
