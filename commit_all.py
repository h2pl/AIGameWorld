import subprocess

repo = r"E:\Projects\SimGameWorld"

# Add all changes in the SimGameWorld repo
result = subprocess.run(["git", "-C", repo, "add", "."], capture_output=True, text=True)
print("add rc:", result.returncode)
if result.stderr:
    print("add stderr:", result.stderr[:200])

# Also add the nodes directory
result = subprocess.run(["git", "-C", repo, "add", "backend/src/nodes/"], capture_output=True, text=True)
print("add_nodes rc:", result.returncode)

msg = """refactor: 拆分 nodes/ 层，实现 Graph-Subgraph-Node-Service-Tool 5 层架构

- 新增 nodes/ 目录，9 个 node 文件作为 State <-> Service 胶水层
  - dm_nodes / world_nodes / character_nodes / combat_nodes
  - dialogue_nodes / exploration_nodes / quest_nodes
  - reflection_nodes / summarizer_nodes

- engine/ 去 graph 化：所有 *_node() 改为纯 Service 函数
  - dm_create/dm_narrate (原 dm_create_node/dm_narrate_node)
  - pc_decide/actor_decide (原 pc_decide_node/actor_decide_node)
  - resolve_combat/dialogue/exploration (原 *_node)
  - check_quests (原 check_quests_node)
  - reflect/summarize (原 reflect_node/summarize_node)

- graph/subgraphs/ 精简：移除内嵌 adapter，改为 import nodes/
  - 所有子图统一使用 StateGraph(dict) schema

- Import 链单向: graph/ -> nodes/ -> engine/ -> storage/

- 41 unit tests green
- 23 integration tests green

--- CodeBuddy (DeepSeek-V4-Pro)"""

with open(r"E:\Projects\SimGameWorld\msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)

result = subprocess.run(["git", "-C", repo, "commit", "-F", r"E:\Projects\SimGameWorld\msg.txt"], capture_output=True, text=True)
print("commit rc:", result.returncode)
print("commit stdout:", result.stdout[-200:] if result.stdout else "")

result = subprocess.run(["git", "-C", repo, "push", "origin", "develop"], capture_output=True, text=True)
print("push rc:", result.returncode)
print("push stderr:", result.stderr[-200:] if result.stderr else "")
