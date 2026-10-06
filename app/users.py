"""User accounts: storage, password hashing, and credential checks.

Passwords are only ever stored as argon2 hashes. Nothing here logs a password.
"""
from __future__ import annotations

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
    password_hash text not null
)
"""

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


def create_user(database: Path, *, email: str, password: str, role: str,
                display_name: str, title: str = "", term: str = "") -> int:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
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
