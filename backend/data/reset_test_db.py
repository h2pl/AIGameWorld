"""重置测试 DB——删→建 schema→导入 pack，只针对 test.db.

用法:
    python data/reset_test_db.py                          # 默认 pack
    python data/reset_test_db.py --pack forgotten_realms  # 指定 pack
    python data/reset_test_db.py --no-pack                # 不导入 pack
"""

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "src" / "storage" / "schema.sql"
DB_PATH = ROOT / "data" / "test.db"
PACK_DIR = ROOT.parent / "world-pack"


def reset() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    print(f"Schema: {DB_PATH.name}")


def import_pack(pack_name: str) -> None:
    pack = PACK_DIR / pack_name
    if not pack.exists():
        print(f"Pack:   {pack_name} not found, skipped")
        return
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "src.cli", "import", str(pack), "--db", str(DB_PATH)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        print(f"Pack:   {pack_name}")
    else:
        print(f"Pack:   FAILED\n{result.stderr}")


def stats() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    for t in (
        "worlds",
        "player_characters",
        "actors",
        "scenes",
        "items",
        "scene_objects",
        "tick_messages",
        "tick_events",
        "dm_records",
    ):
        c.execute("SELECT COUNT(*) FROM " + t)  # noqa: S608
        print(f"  {t:20s} {c.fetchone()[0]}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Reset test DB")
    parser.add_argument("--pack", default="forgotten_realms")
    parser.add_argument("--no-pack", action="store_true")
    args = parser.parse_args()

    print(f"Reset: {DB_PATH.name}\n")
    reset()
    if not args.no_pack:
        import_pack(args.pack)
    print()
    stats()
    print("Done.")


if __name__ == "__main__":
    main()
