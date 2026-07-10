"""运行 prompt 评估 / Run prompt evaluation with LangSmith.

所有评估器都在代码中 inline（format / constraints / quality），不依赖 LangSmith UI 或 hub。
评估结果在 LangSmith 实验结果页查看。

用法 / Usage:
    # 评估 dm_create
    uv run python scripts/run_eval.py --purpose dm_create

    # 指定 experiment 前缀
    uv run python scripts/run_eval.py --purpose dm_create --prefix v1_baseline

    # 使用 variant 文件评估（A/B 测试 variant 版本）
    uv run python scripts/run_eval.py --purpose dm_create --variant-file prompts/dm/dm_create_v2.jinja

环境变量 / Env:
    LANGCHAIN_API_KEY     - LangSmith API key
    LANGCHAIN_PROJECT     - 项目名（默认 aigameworld）
    DEEPSEEK_API_KEY      - DeepSeek API key（用于 quality judge）
    评估时自动禁用 tracing：LANGCHAIN_TRACING_V2=false, LANGFUSE_ENABLED=false
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# 加载 .env 文件 / Load .env file
from dotenv import load_dotenv

# 切换到 backend 目录并加入 sys.path / Switch to backend dir and add to sys.path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env")
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

# 评估时禁用 tracing（避免评估本身产生 trace）/ Disable tracing during eval
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGFUSE_ENABLED"] = "false"

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langsmith import Client
from langsmith.evaluation import aevaluate

from src.config import load_config
from src.eval.evaluators import get_evaluators
from src.llm.llm_client import LLMClient
from src.prompts.prompt_loader import PromptLoader
from src.utils.logging import get_logger

logger = get_logger(__name__)


def build_judge_llm(config) -> ChatOpenAI:
    """构建 judge LLM（用 deepseek）/ Build judge LLM for quality evaluator.

    复用 dm_create 的模型配置 + provider 的 api_key，构建 ChatOpenAI 做 LLM-as-Judge。
    不依赖 LangSmith hub，纯本地调用。
    """
    provider = config.llm.providers.primary
    model_cfg = config.llm.dm_create
    api_key = os.environ.get(provider.api_key_env, "")
    return ChatOpenAI(
        model=model_cfg.model,
        base_url=model_cfg.base_url or provider.base_url,
        api_key=api_key,
        temperature=0.3,  # judge 用低温度保证稳定
        timeout=30,
    )


def _parse_messages(messages_raw: list) -> list:
    """将 LangSmith 格式的 messages 转回 LangChain 消息 / Convert messages back."""
    parsed = []
    for msg_list in messages_raw:
        if isinstance(msg_list, list):
            for m in msg_list:
                role = m.get("type", m.get("role", ""))
                content = m.get("content", "")
                if role == "system":
                    parsed.append(SystemMessage(content=content))
                else:
                    parsed.append(HumanMessage(content=content))
        elif isinstance(msg_list, dict):
            role = msg_list.get("type", msg_list.get("role", ""))
            content = msg_list.get("content", "")
            if role == "system":
                parsed.append(SystemMessage(content=content))
            else:
                parsed.append(HumanMessage(content=content))
    return parsed


def build_target(
    purpose: str,
    llm_client: LLMClient,
    variant_file: Path | None = None,
):
    """构建评估目标函数 / Build target function for evaluation.

    Args:
        purpose: prompt 用途（如 dm_create, pc_decision）
        llm_client: LLM 客户端
        variant_file: 可选的 variant human prompt 文件（A/B 测试用）

    target 接收 dataset 的 inputs，自动识别格式：
    - 含 "messages" 键：旧格式（渲染后 messages，直接传给 LLM）
    - 不含 "messages" 键：新格式（fixture 模板参数，用 PromptLoader 渲染）
    """

    loader = PromptLoader(
        prompts_root=BACKEND_DIR / "src" / "prompts",
        variant_file=variant_file,
    )

    async def target(inputs: dict) -> dict:
        if "messages" in inputs:
            # 旧格式：dataset 中的渲染后 messages
            parsed = _parse_messages(inputs["messages"])
        else:
            # 新格式：fixture 模板参数，用 PromptLoader 渲染
            parsed = loader.render_messages(purpose, **inputs)

        result = await llm_client.call_structured(purpose, _get_schema(purpose), parsed)
        return {"result": result.model_dump()}

    return target


def _get_schema(purpose: str):
    """获取 purpose 对应的 output schema / Get output schema for purpose."""
    from src.schemas.llm_output import DMOutput, PCDecideSchema

    return {"dm_create": DMOutput, "pc_decision": PCDecideSchema}.get(purpose)


async def run_evaluation(
    purpose: str,
    dataset_name: str,
    experiment_prefix: str,
    variant_file: Path | None = None,
) -> None:
    """运行评估 / Run evaluation.

    所有评估器都 inline 在代码中（format / constraints / quality），不依赖 LangSmith UI 或 hub。
    参考: https://docs.langchain.com/langsmith/evaluate-llm-application

    Args:
        purpose: prompt 用途
        dataset_name: LangSmith dataset 名称
        experiment_prefix: experiment 前缀
        variant_file: 可选的 variant prompt 文件（A/B 测试用）
    """
    # 加载配置 / Load config
    config = load_config(str(BACKEND_DIR.parent / "config.yaml"))
    llm_client = LLMClient(config)

    # 构建 target / Build target
    target = build_target(purpose, llm_client, variant_file=variant_file)

    # 构建所有 inline 评估器 / Build all inline evaluators
    judge_llm = build_judge_llm(config)
    inline_evaluators = get_evaluators(purpose, judge_llm=judge_llm)
    logger.info(
        "inline 评估器已加载: %s（judge=%s）",
        [getattr(e, '__name__', 'evaluator') for e in inline_evaluators],
        config.llm.dm_create.model,
    )

    # 运行评估 / Run evaluation
    client = Client()
    experiment_name = f"{purpose}_{experiment_prefix}"

    variant_info = f", variant_file={variant_file.name}" if variant_file else ""
    logger.info("开始评估: experiment=%s, dataset=%s%s", experiment_name, dataset_name, variant_info)

    results = await aevaluate(
        target,
        data=dataset_name,
        evaluators=inline_evaluators,
        experiment_prefix=experiment_name,
        client=client,
    )

    logger.info("评估完成！查看结果: https://smith.langchain.com/o/default/projects/p/aigameworld")


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 prompt 评估")
    parser.add_argument(
        "--purpose",
        required=True,
        choices=["dm_create", "pc_decision"],
        help="评估的 prompt purpose",
    )
    parser.add_argument(
        "--dataset-name",
        default=None,
        help="Dataset 名称（默认 {purpose}_fixture）",
    )
    parser.add_argument(
        "--prefix",
        default="baseline",
        help="experiment 前缀（默认 baseline）",
    )
    parser.add_argument(
        "--variant-file",
        type=Path,
        default=None,
        help="variant human prompt 文件路径（A/B 测试用）；不指定则用默认 .jinja",
    )
    args = parser.parse_args()

    dataset_name = args.dataset_name or f"{args.purpose}_fixture"
    asyncio.run(
        run_evaluation(
            args.purpose,
            dataset_name,
            args.prefix,
            variant_file=args.variant_file,
        )
    )


if __name__ == "__main__":
    main()
