"""Mock 数据路由 / Mock data routes.

注入 mock 数据的逻辑统一放在这里，server.py 只负责注册，不直接包含 mock 逻辑.
"""

import sys
from pathlib import Path

from fastapi import APIRouter, Request

from src.utils.logging import log_api

# 允许从 backend/data 导入 mock.py
_BACKEND_ROOT = Path(__file__).parent.parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from data.mock import seed_mock_data  # noqa: E402

router = APIRouter(prefix="/api/mock", tags=["mock"])


@router.post("/seed")
async def mock_seed(request: Request):
    """按需注入 mock 数据 / Seed mock data on demand."""
    db = request.app.state.db
    await seed_mock_data(db)
    log_api("mock.seed", "-")
    return {"status": "ok"}


__all__ = ["router"]
