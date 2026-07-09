"""评估 API 路由 / Evaluation API routes."""

from pathlib import Path

from fastapi import APIRouter, Query, Request

from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/eval", tags=["eval"])

# Golden Dataset 目录 / Golden dataset directory
_GOLDEN_DIR = Path(__file__).parent.parent.parent / "evals" / "golden_dataset"


def _get_eval_store(request: Request):
    """从 app.state 获取 EvalStore / Get EvalStore from app.state."""
    return getattr(request.app.state, "eval_store", None)


@router.get("/datasets")
async def list_datasets():
    """列出可用的 Golden Dataset / List available golden datasets."""
    from src.evals.evaluator import load_golden_dataset

    datasets = []
    if _GOLDEN_DIR.is_dir():
        for f in _GOLDEN_DIR.iterdir():
            if f.suffix == ".yaml":
                name = f.stem
                data = load_golden_dataset(name)
                datasets.append({"name": name, "cases": len(data)})
    return {"datasets": datasets}


@router.get("/results")
async def get_eval_results(
    dataset: str = Query("", description="数据集名 / Dataset name"),
    dimension: str = Query("", description="评估维度 / Evaluation dimension"),
    last_n: int = Query(50, description="最近 N 条 / Last N records"),
    request: Request = None,
):
    """获取评估结果 / Get evaluation results."""
    store = _get_eval_store(request)
    if not store:
        return {"results": [], "message": "eval store not initialized"}
    results = await store.get_recent(dataset=dataset, dimension=dimension, last_n=last_n)
    return {"results": results}


@router.get("/trend")
async def get_score_trend(
    dimension: str = Query("", description="评估维度 / Evaluation dimension"),
    last_n: int = Query(50, description="最近 N 条 / Last N records"),
    request: Request = None,
):
    """获取评分趋势 / Get score trend."""
    store = _get_eval_store(request)
    if not store:
        return {"trend": [], "message": "eval store not initialized"}
    trend = await store.get_score_trend(dimension=dimension, last_n=last_n)
    return {"trend": trend}


@router.post("/run")
async def run_evaluation(
    dataset: str = Query(..., description="数据集名 / Dataset name"),
    request: Request = None,
):
    """手动触发评估（L1 确定性检查）/ Trigger evaluation (L1 deterministic checks).

    注意：L2 LLM-as-Judge 评估需要在测试环境中运行，不通过 API 触发。
    """
    from src.evals.evaluator import check_chinese_ratio, check_length, load_golden_dataset

    data = load_golden_dataset(dataset)
    if not data:
        return {"error": f"dataset '{dataset}' not found"}

    # L1 检查结果 / L1 check results
    results = []
    for case in data:
        l1 = {
            "case_id": case.get("id", ""),
            "length_check": None,
            "chinese_ratio_check": None,
        }
        # 对 context 中的描述文本做 L1 检查
        ctx = case.get("context", {})
        desc = ctx.get("scene_description", "")
        if desc:
            l1["length_check"] = check_length(desc)
            l1["chinese_ratio_check"] = check_chinese_ratio(desc)
        results.append(l1)

    return {"dataset": dataset, "total_cases": len(data), "l1_results": results}
