---
name: world-builder
description: 根据用户指定的主题（如仙侠、魔兽、蒸汽朋克、科幻等），生成一个完整的 AIGameWorld 世界，并通过 POST /api/world/create 接口写入数据库。生成内容包括世界观、场景、玩家角色(PC)、NPC、物品、场景物体。Use when the user wants to create a new themed world in AIGameWorld, or says "新建世界/创建世界/造一个XX主题的世界".
license: MIT
metadata:
  author: AIGameWorld
  version: "1.0"
---

# World Builder — 按主题新建 AIGameWorld 世界

## 核心流程

1. **明确主题**：从用户需求中提取主题（如仙侠、魔兽、蒸汽朋克、克苏鲁、科幻末世等）。
2. **生成世界数据**：根据主题生成完整世界定义（world + scenes + pcs + actors + items + scene_objects）。
3. **调用接口写入**：调用 `POST /api/world/create` 落库。
4. **验证**：调用 `GET /api/world/{world_id}/state` 确认写入成功。

## 数据生成规范

### world（世界观）
- `id`：英文小写连字符（如 `steampunk`、`xianjian2`）。
- `name`：主题化中文名称（如"蒸汽朋克·铜城"）。
- `description`：**完整的主题世界观**（2-4 句），包含背景、势力、冲突、氛围，供 DM 引擎注入 prompt。
- `rule_set`：主题规则名（如 `steampunk`、`wuxia`）。
- `starting_scene_id`：指向第一个场景 id。
- `status`：`init`（后端 world_init 会自动初始化）。

### scenes（场景，复用现有 Tuxemon 地图资源）
- 每个世界建议 2-4 个场景（城镇 + 室内/副本）。
- **地图资源复用现有 Tuxemon 地图**（避免前端无地图可渲染）：
  - `azure_town` → `assets/tuxemon/maps/azure_town.json`（城镇，50×50）
  - `taba_town` → `assets/tuxemon/maps/taba_town.json`（城镇，64×60）
  - `water_cathedral` → `assets/tuxemon/maps/water_cathedral.json`（水域，50×60）
  - `spyder_cotton_tunnel` → `assets/tuxemon/maps/spyder_cotton_tunnel.json`（室内洞穴，40×20）
- `id`：用 `{world_id}_{场景}` 前缀避免冲突。
- `name`/`description`/`type`：按主题生成（如"蒸汽工业区"）。
- `ext_json.tilemap_url` 指向复用的地图 JSON；`tilesets` 用对应地图的 tileset。
- `tilemap_summary`：简单 JSON（含 type + full_interpretation 主题化解读）。

### pcs（玩家角色，2-4 个）
- 每个 PC 含完整背景：`long_term_goal`（长期目标）、`values_json`（价值观数组）、`arc_json`（角色弧）、`relationships_json`（人际关系）、`personality`（性格）、`equipment_json`、`inventory_json`。
- 主题化命名与职业（如机械师·艾伦、炼金术士·薇拉）。
- `scene_id` 指向 starting 场景。

### actors（NPC，2-4 个）
- 分友好 NPC（`disposition: neutral/friendly`）和敌人/Boss（`hostile`）。
- 敌/Boss 放第二个场景，友好 NPC 放 starting 场景。
- 含 `personality`、`functions_json`（如 `["merchant","dialogue"]` 或 `["enemy","boss"]`）。

### items（物品，2-4 个）
- 主题化物品（如"蒸汽核心钥匙"），`item_type` 用现有枚举（weapon/armor/potion/key/misc 等）。

### scene_objects（场景物体，1-2 个）
- 主题化物体（如"蒸汽控制台"），`object_type` 用现有枚举（container/door/mechanism/decoration 等），`scene_id` 指向 starting 场景。

## 调用接口

用 `scripts/build_world.py` 或直接构造 JSON 调用：

```bash
# 通过脚本（推荐）：脚本会生成主题数据并调用接口
python skills/world-builder/scripts/build_world.py --theme "蒸汽朋克" --name "蒸汽朋克·铜城"

# 或手动构造 JSON 调接口
curl -X POST http://localhost:8000/api/world/create \
  -H "Content-Type: application/json" \
  -d '{"world": {...}, "scenes": [...], "pcs": [...], "actors": [...], "items": [...], "scene_objects": [...]}'
```

## 验证

```bash
curl http://localhost:8000/api/world/{world_id}/state
# 应返回新建世界的 scenes/pcs/actors/items
```

## 注意

- 场景地图**必须复用现有 Tuxemon 资源**，否则前端无法渲染。
- `id` 唯一，避免与已有世界冲突。
- 所有文本用简体中文（专有名词保留原文），与项目 prompt 语言约束一致。
