import logging
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)


class Neo4jRepo:
    """Neo4j Graph Database Repository for Semantic Memory (GraphRAG)."""

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

    async def close(self) -> None:
        """Close the database driver."""
        await self.driver.close()

    async def verify_connectivity(self) -> None:
        """Verify connection to Neo4j database."""
        try:
            await self.driver.verify_connectivity()
            logger.info("Neo4j connectivity verified.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def merge_node(self, label: str, properties: Dict[str, Any], merge_key: str = "id") -> Optional[Dict[str, Any]]:
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
        rel_props: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Merge a relationship between two nodes."""
        rel_props = rel_props or {}
        query = f"""
        MATCH (a:{start_label} {{{start_key}: $start_val}})
        MATCH (b:{end_label} {{{end_key}: $end_val}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $rel_props
        RETURN r
        """
        async with self.driver.session() as session:
            result = await session.run(
                query,
                start_val=start_val,
                end_val=end_val,
                rel_props=rel_props,
            )
            record = await result.single()
            return dict(record["r"]) if record else None

    async def get_ego_graph(self, label: str, key: str, val: Any, depth: int = 1) -> List[str]:
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

    async def get_semantic_context(self, pc_id: str, location_id: Optional[str] = None) -> str:
        """Get semantic memory context for prompt injection."""
        context_lines = []

        # 1. Get PC's relationships (who they know, what they own)
        query_pc = """
        MATCH (pc:Actor {id: $pc_id})-[r]->(target)
        RETURN type(r) as rel_type, target.name as target_name, target.id as target_id, properties(r) as rel_props
        """
        async with self.driver.session() as session:
            result = await session.run(query_pc, pc_id=pc_id)
            async for record in result:
                rel_type = record["rel_type"]
                target_name = record["target_name"] or record["target_id"]
                context_lines.append(f"You {rel_type} {target_name}.")

        # 2. Get Location context if provided
        if location_id:
            query_loc = """
            MATCH (loc:Location {id: $location_id})<-[r:LOCATED_IN]-(actor:Actor)
            WHERE actor.id <> $pc_id
            RETURN actor.name as actor_name
            """
            async with self.driver.session() as session:
                result = await session.run(query_loc, location_id=location_id, pc_id=pc_id)
                actors_in_loc = []
                async for record in result:
                    actors_in_loc.append(record["actor_name"])
                if actors_in_loc:
                    context_lines.append(f"Also in this location: {', '.join(actors_in_loc)}.")

        return "\\n".join(context_lines)
