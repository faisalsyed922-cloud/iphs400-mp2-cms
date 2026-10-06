"""User accounts: storage, password hashing, and credential checks.

Passwords are only ever stored as argon2 hashes. Nothing here logs a password.
"""
from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

ROLES = ("admin", "editor")

_SCHEMA = """
create table if not exists users (
    id integer primary key,
    email text not null unique,
    display_name text not null,
    title text not null default '',
    term text not null default '',
    role text not null check (role in ('admin', 'editor')),
    is_active integer not null default 1,
    password_hash text not null,
    must_change_password integer not null default 0
)
"""

_SETTINGS_SCHEMA = """
create table if not exists settings (
    key text primary key,
    value text not null
)
"""

MIN_PASSWORD = 12


def password_problem(password: str) -> str | None:
    """The one place the password rule lives: a message if it fails, else None."""
    if len(password) < MIN_PASSWORD:
        return f"The password must be at least {MIN_PASSWORD} characters."
    return None


class LastAdmin(Exception):
    """The change would leave the chapter with no active Admin."""


_hasher = PasswordHasher()
# Verified against when the email is unknown, so both failures take similar time.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def connect(database: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(database: Path) -> None:
    with connect(database) as conn:
        conn.execute(_SCHEMA)
        columns = {r["name"] for r in conn.execute("pragma table_info(users)")}
        if "must_change_password" not in columns:
            conn.execute("alter table users add column must_change_password"
                         " integer not null default 0")
        conn.execute(_SETTINGS_SCHEMA)


def create_user(database: Path, *, email: str, password: str, role: str,
                display_name: str, title: str = "", term: str = "") -> int:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    problem = password_problem(password)
    if problem:
        raise ValueError(problem)
    with connect(database) as conn:
        cur = conn.execute(
            "insert into users (email, display_name, title, term, role,"
            " password_hash) values (?, ?, ?, ?, ?, ?)",
            (email.strip().lower(), display_name, title, term, role,
             _hasher.hash(password)),
        )
        return cur.lastrowid


def get_user(database: Path, user_id: int) -> sqlite3.Row | None:
    with connect(database) as conn:
        return conn.execute("select * from users where id = ?",
                            (user_id,)).fetchone()


def authenticate(database: Path, email: str, password: str) -> sqlite3.Row | None:
    """Return the active user for these credentials, or None for any failure."""
    with connect(database) as conn:
        user = conn.execute("select * from users where email = ?",
                            (email.strip().lower(),)).fetchone()
    stored = user["password_hash"] if user else _DUMMY_HASH
    try:
        _hasher.verify(stored, password)
    except (VerifyMismatchError, InvalidHashError):
        return None
    if user is None or not user["is_active"]:
        return None
    return user


def get_user_by_email(database: Path, email: str) -> sqlite3.Row | None:
    with connect(database) as conn:
        return conn.execute("select * from users where email = ?",
                            (email.strip().lower(),)).fetchone()


def set_password(database: Path, user_id: int, password: str, *,
                 temporary: bool = False) -> None:
    """Store a new argon2 hash. A temporary one must be changed at next login."""
    problem = password_problem(password)
    if problem:
        raise ValueError(problem)
    with connect(database) as conn:
        conn.execute("update users set password_hash = ?,"
                     " must_change_password = ? where id = ?",
                     (_hasher.hash(password), int(temporary), user_id))


def verify_password(user: sqlite3.Row, password: str) -> bool:
    try:
        return _hasher.verify(user["password_hash"], password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def make_temporary_password() -> str:
    return secrets.token_urlsafe(12)


def list_users(database: Path) -> list[sqlite3.Row]:
    with connect(database) as conn:
        return conn.execute(
            "select * from users order by is_active desc, display_name").fetchall()


def _other_active_admins(conn: sqlite3.Connection, user_id: int) -> int:
    return conn.execute(
        "select count(*) from users where role = 'admin' and is_active = 1"
        " and id != ?", (user_id,)).fetchone()[0]


def _would_orphan_admin(conn: sqlite3.Connection, user_id: int) -> bool:
    """True if user_id is the only active Admin."""
    current = conn.execute("select role, is_active from users where id = ?",
                           (user_id,)).fetchone()
    return bool(current and current["role"] == "admin" and current["is_active"]
                and _other_active_admins(conn, user_id) == 0)


def update_user(database: Path, user_id: int, *, display_name: str, title: str,
                term: str, role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    with connect(database) as conn:
        if role != "admin" and _would_orphan_admin(conn, user_id):
            raise LastAdmin
        conn.execute("update users set display_name = ?, title = ?, term = ?,"
                     " role = ? where id = ?",
                     (display_name, title, term, role, user_id))


def deactivate_user(database: Path, user_id: int) -> None:
    """Deactivate, never delete: Posts and Bylines stay."""
    with connect(database) as conn:
        if _would_orphan_admin(conn, user_id):
            raise LastAdmin
        conn.execute("update users set is_active = 0 where id = ?", (user_id,))


def current_admin(database: Path) -> sqlite3.Row | None:
    with connect(database) as conn:
        return conn.execute(
            "select * from users where role = 'admin' and is_active = 1"
            " order by id desc limit 1").fetchone()


def get_setting(database: Path, key: str, default: str = "") -> str:
    with connect(database) as conn:
        row = conn.execute("select value from settings where key = ?",
                           (key,)).fetchone()
    return row["value"] if row else default


def set_setting(database: Path, key: str, value: str) -> None:
    with connect(database) as conn:
        conn.execute("insert into settings (key, value) values (?, ?)"
                     " on conflict(key) do update set value = excluded.value",
                     (key, value))
