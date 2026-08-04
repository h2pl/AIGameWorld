"""A/B 测试：对比 baseline 与 variant prompt 版本 / A/B test baseline vs variant prompts.

评估器在 LangSmith UI 上维护（workspace evaluators），附加到 dataset 后自动触发。

流程：
- baseline：当前 .jinja 模板 → 本地渲染 → LLM → LangSmith 评估
- variant：指定 variant 文件 → 本地渲染 → LLM → LangSmith 评估
- 在 LangSmith UI 上对比两个 experiment 结果

用法 / Usage:
    # 基本 A/B 测试（baseline 用当前 .jinja，variant 用指定文件）
    uv run python scripts/ab_test.py --purpose dm_create \\
        --variant-file prompts/dm/dm_create_v2.jinja

    # 指定 dataset
    uv run python scripts/ab_test.py --purpose dm_create \\
        --variant-file prompts/dm/dm_create_v2.jinja \\
        --dataset-name dm_create_fixture

前置条件 / Prerequisites:
    1. 在 LangSmith UI 的 Evaluators 页面创建评估器
    2. 将评估器附加到 dataset（如 dm_create_fixture）
    3. 如果用 LLM evaluator，在 UI 上配置 Judge 模型

环境变量 / Env:
    LANGCHAIN_API_KEY / LANGSMITH_API_KEY - LangSmith API key
    LANGCHAIN_PROJECT                    - 项目名（默认 aigameworld）
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent.parent / "backend"
PROJECT_DIR = BACKEND_DIR.parent
SCRIPTS_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

# 评估时禁用 tracing / Disable tracing during eval
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGFUSE_ENABLED"] = "false"

from langsmith import Client

from src.utils.logging import get_logger

logger = get_logger(__name__)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def ensure_fixture_dataset(client: Client, purpose: str) -> str:
    """确保 LangSmith 中存在 fixture-based dataset。

    从 scripts/fixtures/{purpose}*.json 加载测试输入参数，
    创建 dataset 和 examples（如果不存在）。

    Returns:
        dataset 名称
    """
    dataset_name = f"{purpose}_fixture"

    # 检查 dataset 是否已存在
    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        logger.info("dataset 已存在: %s（跳过创建）", dataset_name)
        return dataset_name

    # 加载 fixture 文件
    fixture_files = sorted(FIXTURE_DIR.glob(f"{purpose}*.json"))
    if not fixture_files:
        logger.error("未找到 fixture 文件: %s/%s*.json", FIXTURE_DIR, purpose)
        sys.exit(1)

    # 创建 dataset
    client.create_dataset(
        dataset_name=dataset_name,
        description=f"Fixture-based dataset for {purpose} A/B testing",
    )

    for fixture_file in fixture_files:
        fixture = json.loads(fixture_file.read_text(encoding="utf-8"))
        client.create_example(
            inputs=fixture,
            dataset_name=dataset_name,
        )
        logger.info("  添加 example: %s", fixture_file.name)

    logger.info("创建 dataset: %s（%d examples）", dataset_name, len(fixture_files))
    return dataset_name


async def run_experiment(
    purpose: str,
    dataset_name: str,
    experiment_prefix: str,
    variant_file: Path | None = None,
) -> str:
    """运行单个实验 / Run a single experiment.

    Args:
        purpose: prompt 用途
        dataset_name: LangSmith dataset 名称
        experiment_prefix: experiment 前缀
        variant_file: variant prompt 文件（None 表示用当前 .jinja = baseline）

    Returns:
        experiment 名称
    """
    from run_eval import run_evaluation

    experiment_name = f"{purpose}_{experiment_prefix}"
    label = f"variant_file={variant_file.name}" if variant_file else "default .jinja"
    logger.info("运行评估: experiment=%s, %s", experiment_name, label)

    await run_evaluation(
        purpose=purpose,
        dataset_name=dataset_name,
        experiment_prefix=experiment_prefix,
        variant_file=variant_file,
    )
    return experiment_name


async def main_async(args: argparse.Namespace) -> None:
    client = Client()

    # 1. 确保 fixture dataset 存在
    dataset_name = args.dataset_name or ensure_fixture_dataset(client, args.purpose)

    # 2. 检查 variant 文件
    if not args.variant_file:
        logger.error("必须指定 --variant-file 用于 A/B 测试")
        sys.exit(1)
    if not args.variant_file.exists():
        logger.error("variant 文件不存在: %s", args.variant_file)
        sys.exit(1)

    # 3. 运行 baseline 评估（当前 .jinja）
    logger.info("=" * 60)
    logger.info("Phase 1/2: Baseline 评估（当前 .jinja）")
    logger.info("=" * 60)
    baseline_exp = await run_experiment(
        args.purpose,
        dataset_name,
        experiment_prefix="baseline",
        variant_file=None,  # baseline 用默认 .jinja
    )

    # 4. 运行 variant 评估
    logger.info("=" * 60)
    logger.info("Phase 2/2: Variant 评估（%s）", args.variant_file.name)
    logger.info("=" * 60)
    variant_exp = await run_experiment(
        args.purpose,
        dataset_name,
        experiment_prefix="variant",
        variant_file=args.variant_file,
    )

    # 5. 输出对比结果
    logger.info("=" * 60)
    logger.info("A/B 测试完成！")
    logger.info("  Baseline experiment: %s", baseline_exp)
    logger.info("  Variant experiment:  %s", variant_exp)
    logger.info("  对比结果: https://smith.langchain.com/o/default/projects/p/aigameworld")
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A/B 测试 baseline 与 variant prompt（本地文件切换方式）"
    )
    parser.add_argument(
        "--purpose",
        required=True,
        choices=["dm_create", "pc_decision"],
        help="评估的 prompt purpose",
    )
    parser.add_argument(
        "--variant-file",
        type=Path,
        required=True,
        help="variant human prompt 文件路径（如 prompts/dm/dm_create_v2.jinja）",
    )
    parser.add_argument(
        "--dataset-name",
        default=None,
        help="LangSmith dataset 名称（默认自动从 fixture 创建 {purpose}_fixture）",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
