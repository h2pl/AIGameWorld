import pathlib, os

base = pathlib.Path(r"E:\Projects\SimGameWorld\backend\src")
sub = base / "graph" / "subgraphs"

mapping = {
    "character_coordinator_subgraph": "character_subgraph",
    "engine_router_subgraph": "engine_subgraph",
    "reflection_coordinator_subgraph": "reflection_subgraph",
}

# 1. 重命名文件
for old_name, new_name in mapping.items():
    old_path = sub / f"{old_name}.py"
    new_path = sub / f"{new_name}.py"
    if old_path.exists():
        os.rename(old_path, new_path)
        print(f"rename: {old_name}.py -> {new_name}.py")

    # 2. 更新文件内部变量的 coordinator 后缀
    # character_coordinator_subgraph -> character_subgraph
    # build_character_coordinator_subgraph -> build_character_subgraph
    text = new_path.read_text("utf-8")
    text = text.replace(old_name, new_name)
    # Also update function/class names that followed the old pattern
    for role in ["character_coordinator", "engine_router", "reflection_coordinator"]:
        new_role = role.replace("_coordinator", "").replace("_router", "")
        text = text.replace(f"build_{role}_subgraph", f"build_{new_role}_subgraph")
        text = text.replace(f"_{role}_subgraph", f"_{new_role}_subgraph")
    new_path.write_text(text, "utf-8")

# 3. 更新 graph.py
for target in ["graph/graph.py", "../tests/unit/test_graph.py"]:
    p = base / target
    text = p.read_text("utf-8")
    for old_name, new_name in mapping.items():
        text = text.replace(old_name, new_name)
    p.write_text(text, "utf-8")
    print(f"updated: {target}")

print("DONE")
