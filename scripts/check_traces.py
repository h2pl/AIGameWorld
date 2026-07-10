"""查看 dm_service.dm_create chain run 的 child LLM run 结构."""
import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent.parent / "backend"
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGFUSE_ENABLED"] = "false"

os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from langsmith import Client

client = Client()
project = os.getenv("LANGCHAIN_PROJECT", "aigameworld")
print(f"project={project}\n")

# 1. 查找 dm_service.dm_create chain runs
dm_runs = list(client.list_runs(
    project_name=project,
    run_type="chain",
    error=False,
    filter='eq(name, "dm_service.dm_create")',
    limit=2,
))
print(f"=== dm_service.dm_create chain runs (共 {len(dm_runs)} 条) ===")
for r in dm_runs:
    print(f"  id={r.id}, name={r.name}")
    print(f"  inputs keys: {list(r.inputs.keys()) if r.inputs else 'none'}")
    print(f"  outputs keys: {list(r.outputs.keys()) if r.outputs else 'none'}")

print()

# 2. 查找第一条 dm chain run 的 child LLM run
if dm_runs:
    parent_id = str(dm_runs[0].id)
    print(f"=== 查找 parent={parent_id} 的 LLM runs ===")
    child_llm = list(client.list_runs(
        project_name=project,
        run_type="llm",
        error=False,
        filter=f'eq(parent_run_id, "{parent_id}")',
        limit=1,
    ))
    print(f"找到 {len(child_llm)} 条 child LLM runs")
    if child_llm:
        r = child_llm[0]
        print(f"\n--- LLM Run ---")
        print(f"id={r.id}, name={r.name}")
        print(f"\ninputs keys: {list(r.inputs.keys()) if r.inputs else 'none'}")
        # 打印完整 inputs（截断）
        inputs_str = json.dumps(r.inputs, ensure_ascii=False, default=str)
        print(f"inputs (前 2000 字符):\n{inputs_str[:2000]}")
        print(f"\noutputs keys: {list(r.outputs.keys()) if r.outputs else 'none'}")
        outputs_str = json.dumps(r.outputs, ensure_ascii=False, default=str)
        print(f"outputs (前 2000 字符):\n{outputs_str[:2000]}")

print()

# 3. 同样查看 pc_service.decide
pc_runs = list(client.list_runs(
    project_name=project,
    run_type="chain",
    error=False,
    filter='eq(name, "pc_service.decide")',
    limit=2,
))
print(f"=== pc_service.decide chain runs (共 {len(pc_runs)} 条) ===")
for r in pc_runs:
    print(f"  id={r.id}, name={r.name}")

if pc_runs:
    parent_id = str(pc_runs[0].id)
    print(f"\n=== 查找 parent={parent_id} 的 LLM runs ===")
    child_llm = list(client.list_runs(
        project_name=project,
        run_type="llm",
        error=False,
        filter=f'eq(parent_run_id, "{parent_id}")',
        limit=1,
    ))
    print(f"找到 {len(child_llm)} 条 child LLM runs")
    if child_llm:
        r = child_llm[0]
        print(f"\n--- LLM Run ---")
        print(f"id={r.id}, name={r.name}")
        inputs_str = json.dumps(r.inputs, ensure_ascii=False, default=str)
        print(f"inputs (前 1500 字符):\n{inputs_str[:1500]}")
        outputs_str = json.dumps(r.outputs, ensure_ascii=False, default=str)
        print(f"outputs (前 1500 字符):\n{outputs_str[:1500]}")
