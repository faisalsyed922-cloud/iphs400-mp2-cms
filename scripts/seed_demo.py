#!/usr/bin/env python3
"""Create demo data so a grader (and you) can use the CMS immediately.

    uv run python scripts/seed_demo.py

T00 has nothing to seed. As you build content types, extend this so it creates:
  - one admin and one editor (passwords read from .env, never hard-coded)
  - a few posts and pages, at least one draft and one published

The rubric expects this to run clean on a fresh clone with .env.example values
(item E4), because the database itself is never committed.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import posts, settings, users  # noqa: E402


def main() -> int:
    admin_pw = os.environ.get("CMS_ADMIN_PASSWORD")
    editor_pw = os.environ.get("CMS_EDITOR_PASSWORD")
    if not admin_pw or not editor_pw:
        print("Set CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD in .env "
              "(copy .env.example).")
        return 1

    users.init_db(settings.DATABASE_PATH)
    for email, name, role, password in (
        ("admin@example.test", "Demo Admin", "admin", admin_pw),
        ("editor@example.test", "Demo Editor", "editor", editor_pw),
    ):
        try:
            users.create_user(settings.DATABASE_PATH, email=email,
                              password=password, role=role, display_name=name)
            print(f"Created {role} {email}")
        except sqlite3.IntegrityError:
            print(f"{email} already exists; left as is")
    posts.init_posts(settings.DATABASE_PATH)
    editor = users.authenticate(settings.DATABASE_PATH, "editor@example.test",
                                editor_pw)
    existing = {p["slug"] for p in posts.list_posts(settings.DATABASE_PATH)}
    for title, body, publish in (
        ("Welcome to the new chapter site",
         "The **Chi Chapter** now keeps its own news. Read more on our "
         "[chapter page](https://example.org).", True),
        ("Rush announcement (draft)", "Dates still to be confirmed.", False),
    ):
        if posts.slugify(title) in existing:
            continue
        posts.create_post(settings.DATABASE_PATH, author=editor, title=title,
                          slug="", body=body, publish=publish)
        print(f"Created {'Published' if publish else 'Draft'} post: {title}")
    # TODO (later tickets): demo Pages.
    return 0


if __name__ == "__main__":
    sys.exit(main())
