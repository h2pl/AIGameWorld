"""Neo4j Graph Database Repository for Semantic Memory (GraphRAG).

提供关系图谱的写入（merge_relationship 带权重累加）和读取（get_semantic_context 中文输出）。
设计为共享单例，通过 repos["neo4j"] 注入各引擎，避免频繁创建/销毁连接。
"""

import logging
from typing import Any

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)

# 关系类型 → 中文描述映射 / Relationship type to Chinese description
_REL_TYPE_CN: dict[str, str] = {
    "TALKED_TO": "与{target}交谈过",
    "ATTACKED": "曾攻击{target}",
    "PARTY_MEMBER": "与{target}是队友",
    "TRUSTS": "信任{target}",
    "ENEMY_OF": "与{target}为敌",
    "LOCATED_IN": "位于{target}",
}


class Neo4jRepo:
    """Neo4j 图数据库仓储——语义记忆 (GraphRAG)."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "aigameworld",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self._available: bool | None = None  # 延迟检测可用性

    async def close(self) -> None:
        """Close the database driver."""
        await self.driver.close()

    async def verify_connectivity(self) -> bool:
        """Verify connection. Returns True if OK, False otherwise (no raise)."""
        try:
            await self.driver.verify_connectivity()
            self._available = True
            logger.info("Neo4j connectivity verified.")
            return True
        except Exception as e:
            self._available = False
            logger.warning("Neo4j unavailable: %s", e)
            return False

    @property
    def available(self) -> bool:
        """是否可用（需先调用 verify_connectivity）."""
        return self._available is True

    async def merge_node(
        self, label: str, properties: dict[str, Any], merge_key: str = "id"
    ) -> dict[str, Any] | None:
        """Merge a node into the graph.

        Args:
            label: The node label (e.g., Actor, Location)
            properties: The node properties. Must include the merge_key.
            merge_key: The property key used to identify uniqueness.
        """
        if merge_key not in properties:
            raise ValueError(f"merge_key '{merge_key}' must be in properties")

        query = f"""
        MERGE (n:{label} {{{merge_key}: $merge_val}})
        SET n += $props
        RETURN n
        """
        async with self.driver.session() as session:
            result = await session.run(query, merge_val=properties[merge_key], props=properties)
            record = await result.single()
            return dict(record["n"]) if record else None

    async def merge_relationship(
        self,
        start_label: str,
        start_key: str,
        start_val: Any,
        end_label: str,
        end_key: str,
        end_val: Any,
        rel_type: str,
        rel_props: dict[str, Any] | None = None,
        tick: int = 0,
    ) -> dict[str, Any] | None:
        """Merge a relationship with weight accumulation.

        首次创建: since_tick=tick, weight=1
        重复触发: weight += 1, last_tick=tick
        """
        rel_props = rel_props or {}
        query = f"""
        MATCH (a:{start_label} {{{start_key}: $start_val}})
        MATCH (b:{end_label} {{{end_key}: $end_val}})
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r.since_tick = $tick, r.weight = 1, r.last_tick = $tick, r += $rel_props
        ON MATCH SET r.weight = r.weight + 1, r.last_tick = $tick, r += $rel_props
        RETURN r
        """
        async with self.driver.session() as session:
            result = await session.run(
                query,
                start_val=start_val,
                end_val=end_val,
                rel_props=rel_props,
                tick=tick,
            )
            record = await result.single()
            return dict(record["r"]) if record else None

    async def get_ego_graph(self, label: str, key: str, val: Any, depth: int = 1) -> list[str]:
        """Retrieve the ego graph (n-degree connections) for a specific node to use in GraphRAG context."""
        query = f"""
        MATCH p=(n:{label} {{{key}: $val}})-[*1..{depth}]-(m)
        RETURN p
        LIMIT 50
        """
        paths = []
        async with self.driver.session() as session:
            result = await session.run(query, val=val)
            async for record in result:
                path = record["p"]
                # Store string representation of path for now
                paths.append(str(path))
        return paths

    async def get_semantic_context(
        self, pc_id: str, location_id: str | None = None, top_k: int = 8
    ) -> str:
        """获取关系记忆上下文（中文输出，按交互权重排序）."""
        context_lines: list[str] = []

        # 1. 获取 PC 的关系（按 weight 降序，取 top_k）
        query_pc = """
        MATCH (pc:Actor {id: $pc_id})-[r]->(target)
        RETURN type(r) as rel_type, target.name as target_name, target.id as target_id,
               coalesce(r.weight, 1) as weight
        ORDER BY weight DESC
        LIMIT $top_k
        """
        async with self.driver.session() as session:
            result = await session.run(query_pc, pc_id=pc_id, top_k=top_k)
            async for record in result:
                rel_type = record["rel_type"]
                target_name = record["target_name"] or record["target_id"]
                template = _REL_TYPE_CN.get(rel_type, f"{rel_type} {{target}}")
                context_lines.append(template.format(target=target_name))

        # 2. 获取同场景其他角色
        if location_id:
            query_loc = """
            MATCH (loc:Location {id: $location_id})<-[r:LOCATED_IN]-(actor:Actor)
            WHERE actor.id <> $pc_id
            RETURN actor.name as actor_name
            """
            async with self.driver.session() as session:
                result = await session.run(query_loc, location_id=location_id, pc_id=pc_id)
                actors_in_loc = [record["actor_name"] async for record in result]
                if actors_in_loc:
                    context_lines.append(f"当前场景还有：{', '.join(actors_in_loc)}")

        return "\n".join(context_lines)
