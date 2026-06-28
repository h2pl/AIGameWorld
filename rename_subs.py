import pathlib, os

base = pathlib.Path(r"E:\Projects\SimGameWorld\backend\src")

# 重命名 3 个文件
renames = [
    ("graph/subgraphs/character_coordinator.py", "graph/subgraphs/character_coordinator_subgraph.py"),
    ("graph/subgraphs/engine_router.py", "graph/subgraphs/engine_router_subgraph.py"),
    ("graph/subgraphs/reflection_coordinator.py", "graph/subgraphs/reflection_coordinator_subgraph.py"),
]

for old, new in renames:
    os.rename(base / old, base / new)
    print(f"renamed: {old} -> {new}")

# 更新 graph.py 和 test_graph.py 中的 import 路径
for target in ["graph/graph.py", "../tests/unit/test_graph.py"]:
    p = base / target
    text = p.read_text("utf-8")
    text = text.replace(
        ".character_coordinator import",
        ".character_coordinator_subgraph import"
    ).replace(
        ".engine_router import",
        ".engine_router_subgraph import"
    ).replace(
        ".reflection_coordinator import",
        ".reflection_coordinator_subgraph import"
    )
    p.write_text(text, "utf-8")
    print(f"updated imports in: {target}")

print("DONE")
