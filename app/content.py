"""One view over Posts and Pages for the dashboard and the content list.

An item's "owner" is its author (Post) or its Assigned editor (Page), so
"Mine" and the author filter treat both kinds the same way.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.deploy import last_deploy
from app.users import connect

_ITEMS = """
select 'post' as kind, posts.id, posts.title, posts.status, posts.updated_at,
       posts.author_id as owner_id, users.display_name as owner_name
  from posts join users on users.id = posts.author_id
union all
select 'page', pages.id, pages.title, pages.status, pages.updated_at,
       pages.assigned_editor_id, users.display_name
  from pages left join users on users.id = pages.assigned_editor_id
"""


def list_items(database: Path, *, status: str = "", kind: str = "",
               owner_id: int | None = None) -> list[dict]:
    """Posts and Pages, newest change first, each marked with `changed`
    (changed since the last Deploy) and `pending` (needs releasing)."""
    clauses, params = [], []
    if status in ("draft", "published"):
        clauses.append("status = ?")
        params.append(status)
    if kind in ("post", "page"):
        clauses.append("kind = ?")
        params.append(kind)
    if owner_id is not None:
        clauses.append("owner_id = ?")
        params.append(owner_id)
    where = " where " + " and ".join(clauses) if clauses else ""
    with connect(database) as conn:
        rows = conn.execute(f"select * from ({_ITEMS}){where}"
                            " order by updated_at desc, kind, id desc",
                            params).fetchall()
    deployed_at = last_deploy(database)
    items = []
    for row in rows:
        item = dict(row)
        item["changed"] = (item["status"] == "published" if deployed_at is None
                           else item["updated_at"] >= deployed_at)
        item["pending"] = item["status"] == "published" and item["changed"]
        items.append(item)
    return items


def unassigned_pages(database: Path) -> list[sqlite3.Row]:
    with connect(database) as conn:
        return conn.execute("select id, title from pages"
                            " where assigned_editor_id is null"
                            " order by title").fetchall()
