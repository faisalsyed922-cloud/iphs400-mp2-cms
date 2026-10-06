"""Page storage. A Page is standing content: no author, no date on the public site."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.posts import now, slugify
from app.users import connect

_SCHEMA = """
create table if not exists pages (
    id integer primary key,
    title text not null,
    slug text not null unique,
    body text not null default '',
    status text not null default 'draft' check (status in ('draft', 'published')),
    assigned_editor_id integer references users(id),
    show_in_nav integer not null default 0,
    nav_order integer not null default 0,
    is_home integer not null default 0,
    created_at text not null,
    updated_at text not null,
    published_at text,
    slug_locked integer not null default 0
)
"""

_SELECT = ("select pages.*, users.display_name as editor_name from pages"
           " left join users on users.id = pages.assigned_editor_id")


class DuplicateSlug(Exception):
    pass


class HomePage(Exception):
    """The Home page cannot be deleted while other Pages exist."""


def init_pages(database: Path) -> None:
    with connect(database) as conn:
        conn.execute(_SCHEMA)


def get_page(database: Path, page_id: int) -> sqlite3.Row | None:
    with connect(database) as conn:
        return conn.execute(_SELECT + " where pages.id = ?", (page_id,)).fetchone()


def list_pages(database: Path) -> list[sqlite3.Row]:
    with connect(database) as conn:
        return conn.execute(_SELECT + " order by pages.title").fetchall()


def count_unassigned(database: Path) -> int:
    with connect(database) as conn:
        return conn.execute("select count(*) from pages"
                            " where assigned_editor_id is null").fetchone()[0]


def active_editors(database: Path) -> list[sqlite3.Row]:
    with connect(database) as conn:
        return conn.execute("select * from users where role = 'editor'"
                            " and is_active = 1 order by display_name").fetchall()


def is_assignable(database: Path, user_id: int) -> bool:
    return any(u["id"] == user_id for u in active_editors(database))


def _set_home(conn: sqlite3.Connection, page_id: int) -> None:
    conn.execute("update pages set is_home = (id = ?)", (page_id,))


def create_page(database: Path, *, title: str, slug: str, body: str,
                assigned_editor_id: int | None, show_in_nav: bool, nav_order: int,
                is_home: bool, publish: bool = False) -> int:
    stamp = now()
    try:
        with connect(database) as conn:
            first = conn.execute("select count(*) from pages").fetchone()[0] == 0
            cur = conn.execute(
                "insert into pages (title, slug, body, assigned_editor_id,"
                " show_in_nav, nav_order, created_at, updated_at)"
                " values (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, slug or slugify(title), body, assigned_editor_id,
                 int(show_in_nav), nav_order, stamp, stamp))
            page_id = cur.lastrowid
            if is_home or first:  # there is always exactly one Home page
                _set_home(conn, page_id)
            if publish:
                _publish(conn, page_id, stamp)
            return page_id
    except sqlite3.IntegrityError as exc:
        if "pages.slug" in str(exc):
            raise DuplicateSlug from exc
        raise


def update_page(database: Path, page_id: int, *, title: str, body: str,
                slug: str | None, action: str, admin_fields: dict | None = None) -> None:
    """Save changes. `slug` is None when the caller may not change it, and
    `admin_fields` (assigned_editor_id, show_in_nav, nav_order, is_home) is None
    when the caller is not the Admin."""
    stamp = now()
    try:
        with connect(database) as conn:
            conn.execute("update pages set title=?, body=?, updated_at=? where id=?",
                         (title, body, stamp, page_id))
            if slug is not None:
                conn.execute("update pages set slug=? where id=?",
                             (slug or slugify(title), page_id))
            if admin_fields is not None:
                conn.execute(
                    "update pages set assigned_editor_id=?, show_in_nav=?,"
                    " nav_order=? where id=?",
                    (admin_fields["assigned_editor_id"],
                     int(admin_fields["show_in_nav"]), admin_fields["nav_order"],
                     page_id))
                if admin_fields["is_home"]:
                    _set_home(conn, page_id)
            if action == "publish":
                _publish(conn, page_id, stamp)
            elif action == "draft":
                conn.execute("update pages set status='draft' where id=?", (page_id,))
    except sqlite3.IntegrityError as exc:
        if "pages.slug" in str(exc):
            raise DuplicateSlug from exc
        raise


def _publish(conn: sqlite3.Connection, page_id: int, stamp: str) -> None:
    conn.execute("update pages set status='published' where id=?", (page_id,))
    conn.execute("update pages set published_at=?, slug_locked=1 where id=?"
                 " and published_at is null", (stamp, page_id))


def unlock_slug(database: Path, page_id: int) -> None:
    with connect(database) as conn:
        conn.execute("update pages set slug_locked=0 where id=?", (page_id,))


def delete_page(database: Path, page_id: int) -> None:
    with connect(database) as conn:
        page = conn.execute("select is_home from pages where id=?",
                            (page_id,)).fetchone()
        others = conn.execute("select count(*) from pages where id != ?",
                              (page_id,)).fetchone()[0]
        if page and page["is_home"] and others:
            raise HomePage
        conn.execute("delete from pages where id=?", (page_id,))
