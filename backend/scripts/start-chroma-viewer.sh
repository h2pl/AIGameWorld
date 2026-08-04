#!/usr/bin/env bash
# ------------------------------------------------------------------
# 启动 AIGameWorld · ChromaDB Server + 自动打开 Viewer UI
# 运行环境：Git Bash / MSYS2 / WSL / macOS / Linux 的 bash 都可以
#
# 使用方式：
#   1) 直接双击 .sh (Windows Git Bash) 或在终端里:
#        bash start-chroma-viewer.sh
#   2) 可选参数:  --port 8001  --no-browser  --no-viewer  --host 0.0.0.0
#        bash start-chroma-viewer.sh --port 9001 --no-browser
#
# 位置：脚本可以放在 backend/scripts/ 里，也可以移到桌面任意位置——
#      只要最终能根据脚本位置找到项目根（backend/ 目录）即可。
# ------------------------------------------------------------------
set -euo pipefail

# ── 参数解析 ────────────────────────────────────────────────────
PORT=8001
HOST="0.0.0.0"
OPEN_BROWSER=1
NO_VIEWER=""
LOG_LEVEL="info"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)        PORT="$2";       shift 2 ;;
        --host)        HOST="$2";       shift 2 ;;
        --log-level)   LOG_LEVEL="$2";  shift 2 ;;
        --no-browser)  OPEN_BROWSER=0;  shift   ;;
        --no-viewer)   NO_VIEWER="--no-viewer"; shift ;;
        -h|--help)
            cat <<EOF
用法: $0 [--port N] [--host IP] [--no-browser] [--no-viewer] [--log-level L]

参数:
  --port N        监听端口 (默认: 8001)
  --host IP       绑定地址  (默认: 0.0.0.0)
  --log-level L   critical|error|warning|info|debug (默认: info)
  --no-browser    不自动打开浏览器
  --no-viewer     不加载 viewer 路由，只跑纯 ChromaDB + health
  -h, --help      显示帮助
EOF
            exit 0
            ;;
        *)
            echo "未知参数: $1 (使用 $0 --help 查看用法)" >&2
            exit 2
            ;;
    esac
done

# ── 定位 backend 目录（$PROJECT_ROOT/backend） ─────────────────
# 脚本所在位置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 优先顺序：
#   1. $SCRIPT_DIR/..   → 如果脚本在 backend/scripts/ 或 backend/bin/
#   2. $SCRIPT_DIR      → 如果脚本就在 backend/
#   3. $SCRIPT_DIR/../AIGameWorld/backend → 如果脚本在 AIGameWorld 同级
PROJECT_ROOT=""
for candidate in \
    "$SCRIPT_DIR/.." \
    "$SCRIPT_DIR" \
    "$SCRIPT_DIR/../../AIGameWorld/backend"
do
    # 存在 chroma_server.py 入口 + .venv/ 目录（或者 venv 由 uv 提供也行，不强求）
    if [[ -f "$candidate/scripts/chroma_server.py" ]]; then
        PROJECT_ROOT="$(cd "$candidate" && pwd)"
        break
    fi
done

if [[ -z "$PROJECT_ROOT" ]]; then
    cat >&2 <<EOF
[ERROR] 找不到 AIGameWorld backend 目录。
       请确认这个脚本放在 AIGameWorld/backend/scripts/ 下，
       或手动修改本脚本顶部的 PROJECT_ROOT 变量。
       当前脚本目录: $SCRIPT_DIR
EOF
    exit 1
fi

cd "$PROJECT_ROOT"

# ── 确认关键文件 ───────────────────────────────────────────────
CHROMA_SCRIPT="$PROJECT_ROOT/scripts/chroma_server.py"
CHROMA_DATA="$PROJECT_ROOT/data/chroma"
mkdir -p "$CHROMA_DATA"

if [[ ! -f "$CHROMA_SCRIPT" ]]; then
    echo "[ERROR] 找不到入口文件: $CHROMA_SCRIPT" >&2
    exit 1
fi

# ── 端口占用检测 ───────────────────────────────────────────────
check_port() {
    local p=$1
    # 跨平台检测（Git Bash + netstat fallback）
    if command -v netstat >/dev/null 2>&1; then
        if netstat -an 2>/dev/null | grep -E "(LISTENING|LISTEN)" | awk '{print $4}' | grep -qE "[:.]${p}$"; then
            return 0
        fi
    fi
    if command -v lsof >/dev/null 2>&1; then
        if lsof -iTCP:"$p" -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

if check_port "$PORT"; then
    cat <<EOF >&2
[警告] 端口 $PORT 已经被占用。
       可能是 ChromaDB Server 已经在运行，或者其他程序占用。
       请先关闭占用进程，或换个端口（例如 --port 8002）。
EOF
    # 尝试获取占用进程（仅限有 lsof / netstat 的情况）
    if command -v lsof >/dev/null 2>&1; then
        echo "       占用进程 PID: $(lsof -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null || true)"
    fi
    exit 3
fi

# ── 选择 Python 解释器 ─────────────────────────────────────────
# 优先: uv run python  (项目用 uv 管理的 virtualenv)
# 次选: .venv/Scripts/python  (Windows venv)
# 次选: .venv/bin/python      (POSIX venv)
# 最后: python3 / python
PY_CMD=""
if [[ -d ".venv" ]]; then
    if [[ -f ".venv/Scripts/python.exe" ]]; then
        PY_CMD=".venv/Scripts/python.exe"
    elif [[ -f ".venv/bin/python" ]]; then
        PY_CMD=".venv/bin/python"
    fi
fi
if command -v uv >/dev/null 2>&1 && [[ -f "pyproject.toml" ]]; then
    # uv 可用时优先 uv run（它会自动处理 .venv 和系统环境）
    PY_CMD="uv run python"
fi
if [[ -z "$PY_CMD" ]]; then
    PY_CMD="$(command -v python3 || command -v python || true)"
fi
if [[ -z "$PY_CMD" ]]; then
    echo "[ERROR] 找不到可用的 python 解释器，请先安装 Python 3.11+ 或激活 virtualenv." >&2
    exit 4
fi

# ── 组装启动命令 ───────────────────────────────────────────────
BROWSER_FLAG="--open-browser"
[[ "$OPEN_BROWSER" -ne 1 ]] && BROWSER_FLAG=""

CMD="$PY_CMD scripts/chroma_server.py \
    --host $HOST \
    --port $PORT \
    --log-level $LOG_LEVEL \
    $BROWSER_FLAG \
    $NO_VIEWER"

# ── 友好横幅 ──────────────────────────────────────────────────
VIEWER_URL="http://127.0.0.1:$PORT/viewer"
HEALTH_URL="http://127.0.0.1:$PORT/health"

cat <<EOF

╔══════════════════════════════════════════════════════════════╗
║          AIGameWorld ChromaDB Server + Viewer               ║
╠══════════════════════════════════════════════════════════════╣
║  Project:   $PROJECT_ROOT
║  Python:    $PY_CMD
║  Host:      http://127.0.0.1:$PORT/
║  Health:    $HEALTH_URL
║  Viewer:    $VIEWER_URL
║  Data dir:  $CHROMA_DATA
║  Port free: $(if check_port "$PORT"; then echo "NO (already in use!)"; else echo "yes"; fi)
╚══════════════════════════════════════════════════════════════╝

准备启动 server ...  按 Ctrl+C 退出。

EOF

# 捕获 Ctrl+C 给个优雅提示
trap 'echo ""; echo "[stop] Ctrl+C caught, bye."; exit 0' INT TERM

# ── 执行 ───────────────────────────────────────────────────────
# shellcheck disable=SC2086
exec $CMD
