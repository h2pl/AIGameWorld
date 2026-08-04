"""从 LangSmith traces 构建评估数据集 / Build evaluation datasets from LangSmith traces.

用法 / Usage:
    uv run python scripts/build_dataset.py --purpose dm_create --limit 20
    uv run python scripts/build_dataset.py --purpose pc_decision --limit 20

环境变量 / Env:
    LANGCHAIN_API_KEY     - LangSmith API key
    LANGCHAIN_PROJECT     - 项目名（默认 aigameworld）

数据来源 / Data source:
    从 LangSmith chain runs（如 dm_service.dm_create / pc_service.decide）
    提取其 child LLM run 的 messages（input）和 AIMessage content（output）。
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# 加载 .env 文件 / Load .env file
from dotenv import load_dotenv

# 切换到 backend 目录并加入 sys.path / Switch to backend dir and add to sys.path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

# 评估时禁用 tracing，避免污染 / Disable tracing during evaluation
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGFUSE_ENABLED"] = "false"

os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from langsmith import Client

from src.schemas.llm_output import DMOutput, PCDecideSchema
from src.utils.logging import get_logger

logger = get_logger(__name__)

# purpose → output schema 映射 / purpose to output schema mapping
PURPOSE_SCHEMA = {
    "dm_create": DMOutput,
    "pc_decision": PCDecideSchema,
}

# purpose → LangSmith chain run name 映射 / purpose to chain run name
# chain run 的 name 来自 @traced() 装饰器（module_name.method_name）
PURPOSE_CHAIN_NAME = {
    "dm_create": "dm_service.dm_create",
    "pc_decision": "pc_service.decide",
}


def _extract_messages(llm_inputs: dict) -> list[dict]:
    """从 LLM run 的 inputs 提取简化的 messages 列表.

    LangSmith 序列化的 messages 格式：
        [[{"id": [...], "kwargs": {"content": "...", "type": "system"}, ...}, ...]]
    转换为：[{"role": "system", "content": "..."}, ...]
    """
    raw = llm_inputs.get("messages", [])
    # messages 是嵌套列表 [[...]]，取第一层 / Flatten nested list
    if raw and isinstance(raw[0], list):
        raw = raw[0]

    result = []
    for msg in raw:
        kwargs = msg.get("kwargs", {})
        role = kwargs.get("type", "unknown")
        content = kwargs.get("content", "")
        if content:  # 跳过空 content / Skip empty content
            result.append({"role": role, "content": content})
    return result


def _extract_output(llm_outputs: dict) -> dict | None:
    """从 LLM run 的 outputs 提取解析后的 JSON 结果.

    LangSmith 序列化的 outputs 格式：
        {"generations": [[{"message": {"kwargs": {"content": "JSON..."}}, ...}]]}
    """
    generations = llm_outputs.get("generations", [])
    if not generations or not generations[0]:
        return None

    gen = generations[0][0]
    message = gen.get("message", {})
    kwargs = message.get("kwargs", {})
    content = kwargs.get("content", "")
    if not content:
        return None

    # content 是 JSON 字符串，解析它 / Parse JSON string
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 尝试提取 ```json ... ``` 代码块 / Try extracting from code block
        import re
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        logger.debug("无法解析 LLM output 为 JSON: %s", content[:200])
        return None


async def build_dataset(purpose: str, dataset_name: str, limit: int = 20) -> None:
    """从 LangSmith traces 提取指定 purpose 的 chain runs，构建 Dataset.

    流程：
    1. 查找 chain runs（name=dm_service.dm_create / pc_service.decide）
    2. 对每个 chain run，查找其 child LLM run
    3. 从 LLM run 提取 messages（input）和 AIMessage content（output）
    4. 验证 output 符合 schema 后创建 dataset example
    """
    client = Client()
    schema = PURPOSE_SCHEMA.get(purpose)
    chain_name = PURPOSE_CHAIN_NAME.get(purpose)
    if schema is None or chain_name is None:
        logger.error("不支持的 purpose: %s（支持: %s）", purpose, list(PURPOSE_SCHEMA))
        sys.exit(1)

    project = os.getenv("LANGCHAIN_PROJECT", "aigameworld")
    logger.info("从 project=%s 提取 purpose=%s（chain name=%s）", project, purpose, chain_name)

    # 1. 查找 chain runs / Find chain runs by name
    chain_runs = list(
        client.list_runs(
            project_name=project,
            run_type="chain",
            error=False,
            filter=f'eq(name, "{chain_name}")',
            limit=limit * 2,  # 多取一些，过滤后可能不够
        )
    )
    logger.info("找到 %d 条 chain runs（name=%s）", len(chain_runs), chain_name)

    # 创建或获取 dataset / Create or get dataset
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        logger.info("Dataset 已存在: %s（id=%s）", dataset_name, dataset.id)
    except Exception:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=f"{purpose} prompt 评估数据集（从生产 traces 提取）",
        )
        logger.info("创建 Dataset: %s（id=%s）", dataset_name, dataset.id)

    # 2. 对每个 chain run，查找 child LLM run / For each chain run, find child LLM run
    added = 0
    for chain_run in chain_runs:
        if added >= limit:
            break

        # 查找 child LLM run / Find child LLM run
        child_llm_runs = list(
            client.list_runs(
                project_name=project,
                run_type="llm",
                error=False,
                filter=f'eq(parent_run_id, "{chain_run.id}")',
                limit=1,
            )
        )
        if not child_llm_runs:
            logger.debug("chain run %s 没有 child LLM run，跳过", chain_run.id)
            continue

        llm_run = child_llm_runs[0]
        if not llm_run.inputs or not llm_run.outputs:
            continue

        # 3. 提取 messages 和 output / Extract messages and output
        messages = _extract_messages(llm_run.inputs)
        output = _extract_output(llm_run.outputs)
        if not messages or output is None:
            logger.debug("run %s 提取失败（messages 或 output 为空）", llm_run.id)
            continue

        # 验证 output 符合 schema / Validate output against schema
        try:
            schema(**output)
        except Exception as e:
            logger.debug("跳过 run %s（输出不符合 schema: %s）", llm_run.id, e)
            continue

        # 4. 创建 dataset example / Create dataset example
        inputs = {"purpose": purpose, "messages": messages}
        outputs = {"result": output}
        client.create_example(
            inputs=inputs,
            outputs=outputs,
            dataset_id=dataset.id,
            metadata={
                "source": "langsmith_trace",
                "chain_run_id": str(chain_run.id),
                "llm_run_id": str(llm_run.id),
                "purpose": purpose,
            },
        )
        added += 1
        logger.info("添加 example %d/%d（llm_run_id=%s）", added, limit, llm_run.id)

    logger.info("完成！Dataset %s 共添加 %d 条 examples", dataset_name, added)
    if added == 0:
        logger.warning(
            "未添加任何 example。请检查：\n"
            "1. 项目 %s 中是否有 name=%s 的 chain runs\n"
            "2. 这些 chain runs 是否有 child LLM runs\n"
            "3. LLM output 是否符合 %s schema",
            project, chain_name, schema.__name__,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="从 LangSmith traces 构建评估数据集")
    parser.add_argument(
        "--purpose",
        required=True,
        choices=list(PURPOSE_SCHEMA.keys()),
        help="LLM purpose（如 dm_create / pc_decision）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="最多提取多少条（默认 20）",
    )
    parser.add_argument(
        "--dataset-name",
        default=None,
        help="Dataset 名称（默认 {purpose}_eval）",
    )
    args = parser.parse_args()

    dataset_name = args.dataset_name or f"{args.purpose}_eval"
    asyncio.run(build_dataset(args.purpose, dataset_name, args.limit))


if __name__ == "__main__":
    main()
