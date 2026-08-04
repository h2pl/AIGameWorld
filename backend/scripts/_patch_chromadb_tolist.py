"""临时脚本：在 ChromaDB 1.5.9 源码中 patch 4 处 .tolist() 调用，兼容原生 list embedding.

ChromaDB 源码内部在 HTTP 序列化 embedding 时会调用:
    cast(Embedding, embedding).tolist()
假设 embedding 是 numpy.ndarray。但默认 embedding 函数和部分模型返回的是 Python list，
没有 .tolist()，于是抛 AttributeError: 'list' object has no attribute 'tolist'。

本脚本直接改 site-packages 里的 chromadb/server/fastapi/__init__.py 4 处，变成：
    list(embedding) if isinstance(embedding, list) else cast(Embedding, embedding).tolist()
"""

from __future__ import annotations

import sys
from pathlib import Path

# 找到 ChromaDB fastapi 源码文件
import chromadb.server.fastapi as _m

src_file = Path(_m.__file__)
print("Patching:", src_file)
print("Exists:", src_file.exists())

raw = src_file.read_text(encoding="utf-8")
marker = "cast(Embedding, embedding).tolist()"
print(f"\nOriginal occurrences of '{marker}':", raw.count(marker))

safe_version = """(
                    list(embedding) if isinstance(embedding, list) else cast(Embedding, embedding).tolist()
                )"""
# 注意原代码的缩进是 17 个空格（每行前面有大量空格 + cast...）
# 为了保持语法和结构一致，直接做字符串精确替换
old_pattern = "cast(Embedding, embedding).tolist()"
new_pattern = (
    """(list(embedding) if isinstance(embedding, list) else cast(Embedding, embedding).tolist())"""
)

patched = raw.replace(old_pattern, new_pattern)
print("After replace occurrences of new pattern:", patched.count(new_pattern))

# 写回（保留 .bak 备份）
bak = src_file.with_suffix(".py.bak_tolist_patch")
if not bak.exists():
    bak.write_text(raw, encoding="utf-8")
    print("Backup created:", bak)

src_file.write_text(patched, encoding="utf-8")
print("Patched file written.")

# 验证 4 处都被替换了
verify = src_file.read_text(encoding="utf-8")
left_old = verify.count(old_pattern)
new_count = verify.count(new_pattern)
print(f"\nVerification: remaining old pattern = {left_old}, new safe pattern = {new_count}")
sys.exit(0 if left_old == 0 and new_count >= 4 else 1)
