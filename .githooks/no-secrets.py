#!/usr/bin/env python
"""Pre-commit hook: 检查是否意外提交了 API Key / Check for accidental API key commits.

扫描暂存区变更文件，检测常见的密钥模式。
Scans staged files for common secret patterns.
"""

import re
import subprocess
import sys
from pathlib import Path

# 密钥检测模式 / Secret detection patterns
PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI/DeepSeek API Key"),
    (r"sk-ant-[a-zA-Z0-9_-]{32,}", "Anthropic API Key"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API Key"),
    (r"gh[pousr]_[A-Za-z0-9_]{36,}", "GitHub Token"),
    (r'DEEPSEEK_API_KEY\s*=\s*["\']?\S+', "DeepSeek Key (env)"),
    (r'ANTHROPIC_API_KEY\s*=\s*["\']?\S+', "Anthropic Key (env)"),
    (r'OPENAI_API_KEY\s*=\s*["\']?\S+', "OpenAI Key (env)"),
]

# 白名单文件 / Whitelist files
SKIP_PATTERNS = ["*.lock", "*.pyc", "*.egg-info/*", "*/.pytest_cache/*", "*.sqlite"]


def check_file(filepath: Path) -> list[str]:
    """检查单个文件 / Check a single file."""
    issues = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return issues

    for line_no, line in enumerate(content.split("\n"), 1):
        for pattern, name in PATTERNS:
            if re.search(pattern, line):
                # 跳过注释行中的示例 / Skip comment lines with examples
                stripped = line.strip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith("//")
                    or stripped.startswith("--")
                ):
                    continue
                issues.append(f"  {filepath}:{line_no}: 疑似 {name} / Potential {name}")
                break
    return issues


def main():
    repo_root = Path(__file__).resolve().parents[1]

    # 获取暂存区文件列表 / Get staged files
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    files = [repo_root / f for f in result.stdout.strip().split("\n") if f]

    all_issues = []
    for fpath in files:
        if not fpath.exists():
            continue
        # 跳过匹配的文件 / Skip matching files
        skip = False
        for pattern in SKIP_PATTERNS:
            if fpath.match(pattern):
                skip = True
                break
        if skip:
            continue
        all_issues.extend(check_file(fpath))

    if all_issues:
        print("\nSECURITY: 检测到可能泄露的密钥 / Potential secret leak detected!\n")
        for issue in all_issues:
            print(issue)
        print(
            "\n请从代码中移除密钥，使用环境变量代替 / Remove keys, use env vars instead"
        )
        print(
            "如果这是误报，用 # no-secrets 注释该行 / If false alarm, add # no-secrets"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
