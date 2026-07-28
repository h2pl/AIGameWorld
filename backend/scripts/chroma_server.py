"""启动 ChromaDB HTTP Server，暴露 data/chroma/ 数据给外部可视化工具。"""
import os
import sys
from pathlib import Path

# 确保工作目录在 backend/
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

# 指定 ChromaDB 数据目录（你的实际数据位置）
os.environ["CHROMA_PERSIST_DIRECTORY"] = str(backend_dir / "data" / "chroma")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "chromadb.app:app",
        host="0.0.0.0",
        port=8001,  # 用 8001，避免和 AIGameWorld API (8000) 冲突
        log_level="info",
    )
