"""World Init Service: 整个世界只执行一次的初始化逻辑 / World-scope one-time init.

与 tick_init_service 的区分：
  - world_init 只在「世界首次启动」执行一次，作用域是整个 world：
      * init_world_scenes —— 以 world.starting_scene_id 确定初始主场景
      * init_graph_db    —— 在 Neo4j 中建立 PC 节点 + 主角团内部 PARTY_MEMBER 关系
    由 ensure_world_initialized 守卫：world.status == "ready" 时直接跳过，不重复执行。
  - tick_init 的每个函数都在「每个 tick」执行一次（如出生点分配、事件截屏）。

world_init 已移出主 tick 图：由 orchestrator.run_tick 在每 tick 入口前调用
ensure_world_initialized(world_id) 完成（幂等），主图不再包含 world_init 节点。
"""

from langchain_core.runnables.config import RunnableConfig

from ..domain import PlayerCharacter, World
from ..utils.helpers import get_repo
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


async def _list_available_scenes(config, world_id: str) -> list:
    """列出当前世界可用场景 / list available scenes."""
    scene_repo = get_repo(config, "scene")
    if not scene_repo:
        return []
    return await scene_repo.list_scenes(world_id)


@trace_node("world_init.init_world_scenes")
async def init_world_scenes(world: World, world_id: str, config: RunnableConfig = None) -> str:
    """整个世界只执行一次：确定初始主场景并返回其 id.

    初始场景是 world 导入时就已经确定的（world_pack 从 meta.starting_scene 写入
    world.starting_scene_id），**不是推出来的**——直接采用，不做任何多数派推导或回退。
    这是确定性路径：world.starting_scene_id 一定有值且必存在于场景列表（world_pack
    导入保证），不做「fallback to first scene」之类的错误路径兜底。
    返回值由 ensure_world_initialized 持久化到 world.current_scene_id。
    """
    starting = getattr(world, "starting_scene_id", "")
    if not starting:
        raise ValueError(
            f"[world_init] world {world_id} has no starting_scene_id — world_pack import is broken"
        )

    available = await _list_available_scenes(config, world_id)
    valid_ids = {s.id for s in available}
    if starting not in valid_ids:
        raise ValueError(
            f"[world_init] world {world_id} starting_scene_id={starting!r} "
            f"not found in {len(valid_ids)} available scenes — world_pack import is broken"
        )

    logger.info("[world_init] init_world_scenes scene=%s (world.starting=%s)", starting, starting)
    return starting


@trace_node("world_init.init_graph_db")
async def init_graph_db(pcs: dict[str, PlayerCharacter], config=None) -> dict:
    """整个世界只执行一次：在 Neo4j 初始化 PC 节点与主角团内部关系."""
    if not pcs:
        return {}

    neo4j_repo = get_repo(config, "neo4j")
    if not neo4j_repo:
        logger.warning("[world_init] Neo4j unavailable, skipping graph init")
        return {}

    # 初始化 PC 节点
    for pc in pcs.values():
        await neo4j_repo.merge_node(
            label="Actor", properties={"id": pc.id, "name": pc.name, "type": "pc"}
        )

    # 建立主角团内部的友军关系 (PARTY_MEMBER)
    for pc1 in pcs.values():
        for pc2 in pcs.values():
            if pc1.id != pc2.id:
                await neo4j_repo.merge_relationship(
                    start_label="Actor",
                    start_key="id",
                    start_val=pc1.id,
                    end_label="Actor",
                    end_key="id",
                    end_val=pc2.id,
                    rel_type="PARTY_MEMBER",
                    tick=1,
                )
    return {}


@trace_node("world_init.ensure")
async def ensure_world_initialized(world_id: str, config: RunnableConfig = None) -> None:
    """世界初始化守卫：status == "ready" 时跳过；否则执行一次 world_init 并置 ready.

    幂等：多次调用、被重置后再次调用都安全。由 orchestrator.run_tick 在每 tick 入口前调用，
    因此 world_init 完全在 tick 主图之外完成，主图不再需要首/后续 tick 的条件分流。
    """
    world_repo = get_repo(config, "world")
    if world_repo is None:
        logger.error("[world_init] world repo not found, skip init")
        return

    status = await world_repo.get_status(world_id)
    if status == "ready":
        logger.info("[world_init] world %s already ready, skip init", world_id)
        return

    # 1. 加载 world + pcs（graph 外独立加载）
    world = await world_repo.get(world_id)
    pc_repo = get_repo(config, "char")
    pcs: dict[str, PlayerCharacter] = {}
    if pc_repo and world_id:
        pc_list = await pc_repo.load_all(world_id)
        pcs = {pc.id: pc for pc in pc_list}

    logger.info("[world_init] initializing world %s (pcs=%d)", world_id, len(pcs))

    # 2. 初始化场景（写 current_scene_id）+ Neo4j 图
    scene_id = await init_world_scenes(world, world_id, config=config)
    await world_repo.set_current_scene_id(world_id, scene_id)
    await init_graph_db(pcs, config=config)

    # 3. 标记 ready（持久化）
    await world_repo.set_status(world_id, "ready")
    logger.info("[world_init] world %s is ready (scene=%s)", world_id, scene_id)
