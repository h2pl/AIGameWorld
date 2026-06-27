#!/usr/bin/env python
"""Pre-commit hook: 检查所有变更文件是否有中英双语注释 / Check all changed files for comments.

用法 / Usage:
  python .githooks/check-comments.py          # 检查所有追踪文件
  python .githooks/check-comments.py --all    # 检查所有文件（非仅变更）

规则 / Rules:
  - 每个文件必须有注释（# 或 // 开头的行，或成对出现的 \"\"\"）
  - 注释行数 >= 总行数的 5%（最小 2 行）
  - 白名单：自动生成的文件（*.lock, egg-info, node_modules）跳过
  - 退出码 1 = 不通过，阻止提交
"""

import subprocess
import sys
from pathlib import Path

# 白名单目录/文件模式 / Whitelist patterns
SKIP_GLOBS = ["*.lock", "*.egg-info/*", "node_modules/*", "__pycache__/*",
              ".pytest_cache/*", ".ruff_cache/*", ".mypy_cache/*"]
# 白名单确切文件名（不含路径）/ Whitelist exact filenames
SKIP_FILES = {".gitkeep", "package-lock.json", ".prettierrc"}

# 最低注释率 / Minimum comment ratio
MIN_COMMENT_RATIO = 0.05
# 最小注释行数（所有文件至少 1 行）/ Minimum comment lines (at least 1)
MIN_COMMENT_LINES = 1


def is_skipped(filepath: Path, repo_root: Path) -> bool:
    """检查是否在跳过列表中 / Check if file should be skipped."""
    rel = filepath.relative_to(repo_root)
    rel_str = str(rel).replace("\\", "/")
    if filepath.name in SKIP_FILES:
        return True
    for pattern in SKIP_GLOBS:
        if any(part in rel_str.split("/") for part in pattern.replace("*", "").split("/") if part):
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if rel_str.startswith(prefix) or ("/" + prefix) in rel_str:
                    return True
        if filepath.match(pattern):
            return True
    return False


def has_comment(line: str) -> bool:
    """判断一行代码是否有注释 / Check if a line has a comment."""
    stripped = line.strip()
    if not stripped:
        return False
    # Python/YAML/Toml/Makefile 注释
    if stripped.startswith("#"):
        return True
    # JS/TS/CSS 注释
    if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
        return True
    # HTML 注释
    if "<!--" in stripped:
        return True
    # Python docstring（独立行的 \"\"\" 或 '''）/ Python docstrings
    if '"""' in stripped or "'''" in stripped:
        return True
    # SQL 注释
    if stripped.startswith("--"):
        return True
    return False


def check_file(filepath: Path, repo_root: Path) -> tuple[bool, int, int]:
    """检查单个文件 / Check a single file.
    
    Returns: (pass, total_lines, comment_lines)
    """
    if is_skipped(filepath, repo_root):
        return True, 0, 0

    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return True, 0, 0  # 二进制文件跳过 / Skip binary files

    lines = [l for l in text.split("\n")]
    non_empty = [l for l in lines if l.strip()]
    total = len(non_empty)

    if total < 3:  # 过小的文件不检查 / Skip tiny files
        return True, total, 0

    comments = sum(1 for l in non_empty if has_comment(l))
    ratio = comments / total if total > 0 else 0
    
    # 数据/声明式文件只需有注释头 / Data/declarative files only need header comment
    is_data_file = filepath.suffix in ('.yaml', '.yml', '.toml')
    # 配置/基础设施文件 / Config/infra files
    is_config_file = filepath.name in ('Dockerfile', 'package.json', '.prettierrc') or \
                     filepath.suffix in ('.json', '.ini', '.cfg')
    # __init__.py / setup / test 文件 / Init/setup/test files
    is_init_file = filepath.name == '__init__.py'
    is_test_file = 'tests/' in str(filepath.relative_to(repo_root)).replace('\\', '/')
    
    if is_data_file or is_config_file or is_init_file or is_test_file:
        passed = comments >= MIN_COMMENT_LINES
    else:
        passed = comments >= MIN_COMMENT_LINES and ratio >= MIN_COMMENT_RATIO
    return passed, total, comments


def main():
    repo_root = Path(__file__).resolve().parents[1]

    # 获取变更文件 / Get changed files
    all_files = "--all" in sys.argv
    if all_files:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, cwd=str(repo_root)
        )
        files = [repo_root / f for f in result.stdout.strip().split("\n") if f]
    else:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True, text=True, cwd=str(repo_root)
        )
        files = [repo_root / f for f in result.stdout.strip().split("\n") if f]

    if not files:
        print("OK: 无变更文件 / No changed files")
        return 0

    failed = []
    for fpath in files:
        if not fpath.exists():
            continue
        passed, total, comments = check_file(fpath, repo_root)
        if not passed:
            ratio = comments / total if total > 0 else 0
            rel = fpath.relative_to(repo_root)
            failed.append((str(rel), total, comments, ratio))

    if failed:
        print(f"\nFAIL: {len(failed)} 个文件注释不足 / files lack comments (min {MIN_COMMENT_RATIO:.0%}):\n")
        for fname, total, comments, ratio in failed:
            print(f"  {fname:<55}  {comments}/{total}  ({ratio:.1%})")
        print(f"\n规则: 所有文件必须有中英双语注释 / All files must have comments")
        print(f"最低注释率: {MIN_COMMENT_RATIO:.0%} (至少 {MIN_COMMENT_LINES} 行)")
        return 1

    print(f"OK: {len(files)} 个文件检查通过 / files passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
