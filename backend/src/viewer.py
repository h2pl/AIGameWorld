"""DB 查看器 / DB Viewer — 简单的 HTML 页面展示 pack 数据."""


def _db_query(db_path: str, sql: str, params: tuple = ()) -> list[dict]:
    """查询 SQLite / Query SQLite."""
    import sqlite3  # 延迟导入 / Lazy import

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def render_index(db_path: str) -> str:
    """pack 列表页 / Pack list page."""
    packs: set[str] = set()
    for t in ("player_characters", "actors", "scenes"):  # 所有含 pack_id 的表 / Tables with pack_id
        for r in _db_query(db_path, f"SELECT DISTINCT pack_id FROM {t}"):  # noqa: S608
            packs.add(r["pack_id"])
    items = "".join(f'<li><a href="/view/{p}">{p}</a></li>' for p in sorted(packs) if p)
    return f"<html><body><h1>World Packs</h1><ul>{items}</ul></body></html>"


def render_pack(pack_id: str, db_path: str) -> str:
    """pack 详情页 / Pack detail page."""
    # 参数化查询 / Parameterized queries
    pcs = len(_db_query(db_path, "SELECT id FROM player_characters WHERE pack_id=?", (pack_id,)))
    actors = len(_db_query(db_path, "SELECT id FROM actors WHERE pack_id=?", (pack_id,)))
    items = len(_db_query(db_path, "SELECT id FROM items WHERE pack_id=?", (pack_id,)))
    return f"<html><body><h1>{pack_id}</h1><p>PCs: {pcs}, Actors: {actors}, Items: {items}</p></body></html>"
