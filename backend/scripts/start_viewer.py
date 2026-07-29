"""一键启动 AIGameWorld ChromaDB Server + 自动打开 Viewer UI.

纯 Python 启动器（不依赖 bash/PowerShell/Git Bash）：
  cd E:\\Projects\\AIGameWorld\\backend
  uv run python scripts\\start_viewer.py            # 默认 8001 + 自动开浏览器
  uv run python scripts\\start_viewer.py --help     # 看支持的参数
  python scripts\\start_viewer.py --port 9001 --no-browser

如果没有 uv，只要激活 virtualenv 再跑也行：
  .venv\\Scripts\\activate
  python scripts\\start_viewer.py
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import chroma_server  # 复用同一个脚本的 argparse（不会运行 main，因为它有 __name__ guard）


# ═══════════════════════════════════════════════════════════════════════
# 路径自定位：找到 backend/ 根目录
# ═══════════════════════════════════════════════════════════════════════
def _locate_backend_root() -> Path:
    # 本脚本在 backend/scripts/ 下 → 上一级就是 backend/
    here = Path(__file__).resolve().parent
    if (here / "chroma_server.py").exists() and (here.parent / "pyproject.toml").exists():
        return here.parent
    if (here / "pyproject.toml").exists():
        return here
    # 如果用户把脚本移到桌面或别处：尝试向上找 3 层里有 pyproject.toml 且 scripts/chroma_server.py 的目录
    p = here
    for _ in range(6):
        if (p / "pyproject.toml").exists() and (p / "scripts" / "chroma_server.py").exists():
            return p
        p = p.parent
    raise FileNotFoundError(
        "找不到 backend 根目录（需要包含 pyproject.toml 和 scripts/chroma_server.py）。\n"
        f"请确认 start_viewer.py 还在 AIGameWorld/backend/scripts/ 下。当前脚本目录: {here}"
    )


BACKEND_ROOT = _locate_backend_root()
os.chdir(BACKEND_ROOT)  # 保持与 chroma_server.py 里的 cwd 一致

# ═══════════════════════════════════════════════════════════════════════
# 参数解析（和 chroma_server.py 一一对应，额外加 --wait）
# ═══════════════════════════════════════════════════════════════════════
_p = chroma_server._build_arg_parser()
_p.prog = "start_viewer"
_p.description = (
    "一键启动器：检测端口占用 → 选择可用 python → 调起 chroma_server.py 并 --open-browser。\n"
    "不做任何依赖安装，如果缺依赖（uvicorn/chromadb/requests 等）请先 `uv sync`。"
)
_p.add_argument(
    "--no-kill",
    action="store_true",
    help="检测到端口被占用时不要自动杀进程（默认会自动杀 LISTENING 的占用进程）",
)
_p.add_argument(
    "--wait",
    action="store_true",
    help="server 进程结束后不立即退出，等待用户按回车（适合 .py 脚本被双击打开的场景）",
)
_args = _p.parse_args()

# 默认行为：只要没传 --no-browser，就默认打开
if "--no-browser" not in sys.argv and "-h" not in sys.argv and "--help" not in sys.argv:
    _args.open_browser = True


def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect((host, port))
        except (ConnectionRefusedError, OSError, TimeoutError):
            return False
        else:
            return True


# ═══════════════════════════════════════════════════════════════════════
# 跨平台杀占用端口的 LISTENING 进程（纯标准库，不依赖 psutil）
# ═══════════════════════════════════════════════════════════════════════
import re as _re
import shutil as _shutil


def _kill_process_on_port(port: int, host: str = "127.0.0.1") -> int:
    """杀掉在 host:port 上 LISTEN 的进程。返回杀掉的进程数（0 = 没找到，-1 = 失败）。"""
    pids: list[str] = []
    try:
        if sys.platform.startswith("win"):
            out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                if parts[0] != "TCP":
                    continue
                local = parts[1]
                if not (local.endswith(f":{port}")):
                    continue
                if parts[3] != "LISTENING":
                    continue
                pid = parts[4]
                if pid.isdigit() and pid not in pids:
                    pids.append(pid)
            if pids:
                subprocess.run(
                    ["taskkill", "/F"] + [tok for pid in pids for tok in ("/PID", pid)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
        else:
            # macOS / Linux
            if _shutil.which("lsof"):
                out = subprocess.check_output(
                    ["lsof", "-iTCP", f":{port}", "-sTCP:LISTEN", "-t"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                pids = [p for p in out.splitlines() if p.strip().isdigit()]
            elif _shutil.which("ss"):
                out = subprocess.check_output(
                    ["ss", "-ltnpH", f"sport = :{port}"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                for m in _re.finditer(r"pid=(\d+)", out):
                    pid = m.group(1)
                    if pid.isdigit() and pid not in pids:
                        pids.append(pid)
            if pids:
                subprocess.run(["kill", "-9"] + pids, check=False, capture_output=True, text=True)
        return len(pids)
    except Exception:
        return -1


def _ensure_port_free(port: int, host: str = "127.0.0.1", *, allow_kill: bool) -> None:
    if not _is_port_in_use(port, host):
        return
    if allow_kill:
        print(f"  🔪 端口 {port} 被占用，尝试杀 LISTENING 进程 ...")
        killed = _kill_process_on_port(port, host)
        if killed < 0:
            print(f"  ⚠️  杀进程失败（异常）")
        elif killed == 0:
            print(f"  ⚠️  没找到在 LISTEN 的进程（可能是其他状态占用）")
        else:
            print(f"  ✅ 杀了 {killed} 个占用进程，等待释放 ...")
            time.sleep(1.5)
        if not _is_port_in_use(port, host):
            return
    print(
        f"\n[ERROR] 端口 {port} 仍被占用（自动杀失败或你传了 --no-kill）。\n"
        f"       方案 A：换端口再试 → python scripts\\start_viewer.py --port {port + 1}\n"
        f"       方案 B：手动杀掉占用进程后重跑（Windows: taskkill /F /PID <LISTENING PID>）\n",
        file=sys.stderr,
    )
    sys.exit(3)


def _banner() -> None:
    host_alias = "127.0.0.1" if _args.host == "0.0.0.0" else _args.host
    viewer = f"http://{host_alias}:{_args.port}/viewer"
    health = f"http://{host_alias}:{_args.port}/health"
    data_dir = BACKEND_ROOT / "data" / "chroma"
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          AIGameWorld ChromaDB Server + Viewer (launcher)   ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Project:   {BACKEND_ROOT}")
    print(f"║  Health:    {health}")
    print(f"║  Viewer:    {viewer}")
    print(f"║  Data dir:  {data_dir}")
    print(f"║  Port free: {'no (ALREADY IN USE!)' if _is_port_in_use(_args.port) else 'yes'}")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


_banner()

# ═══════════════════════════════════════════════════════════════════════
# 端口占用检测 + 默认自动杀（传 --no-kill 关掉自动杀）
# ═══════════════════════════════════════════════════════════════════════
_ensure_port_free(_args.port, _args.host, allow_kill=not _args.no_kill)


# ═══════════════════════════════════════════════════════════════════════
# 选择 python 解释器（优先：uv run python，然后 .venv/Scripts/python.exe，最后 sys.executable）
# ═══════════════════════════════════════════════════════════════════════
def _pick_python() -> list[str]:
    # 1) 如果 pyproject.toml 存在且 uv 可用，优先 uv run
    pyproject = BACKEND_ROOT / "pyproject.toml"
    if pyproject.exists():
        # 不用 shutil.which('uv') 也可以，尝试直接调，失败再 fallback
        try:
            r = subprocess.run(
                ["uv", "--version"], check=False, capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                return ["uv", "run", "python"]
        except (FileNotFoundError, PermissionError):
            pass

    # 2) .venv/Scripts/python.exe (Windows) / .venv/bin/python (POSIX)
    for rel in [".venv/Scripts/python.exe", ".venv/bin/python"]:
        p = BACKEND_ROOT / rel
        if p.exists():
            return [str(p)]

    # 3) 当前 sys.executable（如果它已经在 venv 里就 OK）
    return [sys.executable]


PY_ARGS = _pick_python()

# ═══════════════════════════════════════════════════════════════════════
# 拼接命令 → 调 chroma_server.main(...)  其实更简单：直接运行模块文件
# ═══════════════════════════════════════════════════════════════════════
entry = BACKEND_ROOT / "scripts" / "chroma_server.py"
cmd = [*PY_ARGS, str(entry)]

# 参数
cmd += ["--host", _args.host]
cmd += ["--port", str(_args.port)]
cmd += ["--log-level", _args.log_level]
if _args.open_browser:
    cmd += ["--open-browser"]
if _args.no_viewer:
    cmd += ["--no-viewer"]

print("› ", " ".join(cmd))
print()
print("按 Ctrl+C 退出。")
print()

try:
    if _args.wait:
        # 用户希望"结束后等待用户确认"，那么用 Popen 不替换父进程
        proc = subprocess.Popen(cmd)
        try:
            proc.wait()
        except KeyboardInterrupt:
            try:
                proc.terminate()
            except Exception:
                pass
            proc.wait(timeout=5)
        input("\n[done] 按回车关闭窗口…")
    else:
        # 前台执行 → 用户 Ctrl+C 这里退出
        subprocess.run(cmd, check=False)
except KeyboardInterrupt:
    print("\n[stop] Ctrl+C caught, bye.")
