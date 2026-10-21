"""Post storage. A Post's Byline is copied from its author at first Published."""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from app.users import connect

_SCHEMA = """
create table if not exists posts (
    id integer primary key,
    title text not null,
    slug text not null unique,
    body text not null default '',
    status text not null default 'draft' check (status in ('draft', 'published')),
    author_id integer not null references users(id),
    created_at text not null,
    updated_at text not null,
    published_at text,
    slug_locked integer not null default 0,
    byline_name text,
    byline_title text,
    byline_term text,
    category text not null default '',
    tags text not null default ''
)
"""


class DuplicateSlug(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(title: str) -> str:
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "post"


def label_slug(name: str) -> str:
    """Slug for a Label (a Category or Tag name); empty when the name has no usable letters."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean_category(raw: str) -> str:
    name = " ".join(raw.split())
    return name if label_slug(name) else ""


def clean_tags(raw: str) -> str:
    """Normalise a comma-separated tag field: trimmed, no blanks, no repeats."""
    seen, tags = set(), []
    for part in raw.split(","):
        name = " ".join(part.split())
        slug = label_slug(name)
        if slug and slug not in seen:
            seen.add(slug)
            tags.append(name)
    return ", ".join(tags)


def unusable_labels(category: str, tags: str) -> str | None:
    """An error message when a Category or Tag has no usable letters, else None."""
    if category.strip() and not label_slug(category):
        return "A Category needs at least one letter or digit."
    if any(p.strip() and not label_slug(p) for p in tags.split(",")):
        return "Each Tag needs at least one letter or digit."
    return None


def tag_list(post) -> list[str]:
    return [t for t in post["tags"].split(", ") if t]


def init_posts(database: Path) -> None:
    with connect(database) as conn:
        conn.execute(_SCHEMA)


def get_post(database: Path, post_id: int) -> sqlite3.Row | None:
    with connect(database) as conn:
        return conn.execute(
            "select posts.*, users.display_name as author_name from posts"
            " join users on users.id = posts.author_id where posts.id = ?",
            (post_id,)).fetchone()


def list_posts(database: Path) -> list[sqlite3.Row]:
    with connect(database) as conn:
        return conn.execute(
            "select posts.*, users.display_name as author_name from posts"
            " join users on users.id = posts.author_id"
            " order by posts.updated_at desc, posts.id desc").fetchall()


def create_post(database: Path, *, author, title: str, slug: str, body: str,
                publish: bool = False, category: str = "", tags: str = "") -> int:
    stamp = now()
    try:
        with connect(database) as conn:
            cur = conn.execute(
                "insert into posts (title, slug, body, author_id, created_at,"
                " updated_at, category, tags) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, slug or slugify(title), body, author["id"], stamp, stamp,
                 clean_category(category), clean_tags(tags)))
            post_id = cur.lastrowid
            if publish:
                _publish(conn, post_id, author, stamp)
            return post_id
    except sqlite3.IntegrityError as exc:
        if "posts.slug" in str(exc):
            raise DuplicateSlug from exc
        raise


def update_post(database: Path, post_id: int, *, title: str, body: str,
                slug: str | None, action: str, category: str | None = None,
                tags: str | None = None) -> None:
    """Save changes. `slug` is None when the caller may not change it; a
    `category` or `tags` of None is left as it was."""
    stamp = now()
    try:
        with connect(database) as conn:
            if slug is None:
                conn.execute("update posts set title=?, body=?, updated_at=?"
                             " where id=?", (title, body, stamp, post_id))
            else:
                conn.execute("update posts set title=?, body=?, slug=?,"
                             " updated_at=? where id=?",
                             (title, body, slug or slugify(title), stamp, post_id))
            if category is not None:
                conn.execute("update posts set category=? where id=?",
                             (clean_category(category), post_id))
            if tags is not None:
                conn.execute("update posts set tags=? where id=?",
                             (clean_tags(tags), post_id))
            if action == "publish":
                author = conn.execute(
                    "select users.* from users join posts"
                    " on posts.author_id = users.id where posts.id=?",
                    (post_id,)).fetchone()
                _publish(conn, post_id, author, stamp)
            elif action == "draft":
                conn.execute("update posts set status='draft' where id=?",
                             (post_id,))
    except sqlite3.IntegrityError as exc:
        if "posts.slug" in str(exc):
            raise DuplicateSlug from exc
        raise


def _publish(conn: sqlite3.Connection, post_id: int, author, stamp: str) -> None:
    first = conn.execute("select published_at from posts where id=?",
                         (post_id,)).fetchone()["published_at"] is None
    conn.execute("update posts set status='published' where id=?", (post_id,))
    if first:  # published timestamp, Byline and Slug lock are fixed at first publish
        conn.execute(
            "update posts set published_at=?, slug_locked=1, byline_name=?,"
            " byline_title=?, byline_term=? where id=?",
            (stamp, author["display_name"], author["title"], author["term"],
             post_id))


def unlock_slug(database: Path, post_id: int) -> None:
    with connect(database) as conn:
        conn.execute("update posts set slug_locked=0 where id=?", (post_id,))


def delete_post(database: Path, post_id: int) -> None:
    with connect(database) as conn:
        conn.execute("delete from posts where id=?", (post_id,))


def format_byline(name, title, term) -> str:
    return ", ".join(p for p in (name, title, term) if p)


def byline(post) -> str:
    return format_byline(post["byline_name"], post["byline_title"],
                         post["byline_term"])
