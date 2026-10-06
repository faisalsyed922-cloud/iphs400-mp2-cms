"""The `cms` command: serve, publish, deploy.

    uv run cms serve      # admin console + public preview at http://localhost:8000
    uv run cms publish    # render site/ from published content
    uv run cms deploy     # push site/ to the gh-pages branch (Pages serves it)
    uv run cms create-admin EMAIL   # make an Admin; asks for the password
"""
from __future__ import annotations

import argparse
import getpass
import sqlite3
import subprocess
import sys

from app import settings, users
from app.publish import render_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cms")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the admin console locally")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", default=True)
    sub.add_parser("publish", help="render site/ from published content")
    deploy = sub.add_parser("deploy", help="push site/ to gh-pages")
    deploy.add_argument("--message", default="Publish site")
    create = sub.add_parser("create-admin", help="create an Admin account")
    create.add_argument("email")
    create.add_argument("--name", default="Admin", help="display name")
    args = parser.parse_args(argv)

    if args.command == "create-admin":
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Password again: "):
            print("The passwords did not match; nothing was created.")
            return 1
        users.init_db(settings.DATABASE_PATH)
        try:
            users.create_user(settings.DATABASE_PATH, email=args.email,
                              password=password, role="admin",
                              display_name=args.name)
        except sqlite3.IntegrityError:
            print(f"{args.email} already has an account.")
            return 1
        print(f"Created Admin {args.email}.")
        return 0

    if args.command == "serve":
        if settings.SECRET_KEY == settings.DEV_SECRET_KEY:
            print("CMS_SECRET_KEY is not set (copy .env.example to .env and "
                  "change it). Refusing to serve with the public dev key.")
            return 1
        import uvicorn

        uvicorn.run("app.main:app", port=args.port, reload=args.reload)
        return 0

    if args.command == "publish":
        out = render_site()
        print(f"Wrote {out}. Preview it with:  python3 -m http.server -d {out} 8001")
        return 0

    if args.command == "deploy":
        if not settings.SITE.exists():
            print("site/ does not exist yet — run `uv run cms publish` first.")
            return 1
        result = subprocess.run(
            [sys.executable, "-m", "ghp_import", "-n", "-p", "-m", args.message,
             str(settings.SITE)],
        )
        if result.returncode == 0:
            print("Pushed to gh-pages. Settings -> Pages -> Deploy from a branch -> "
                  "gh-pages / root, then wait up to 10 minutes.")
        return result.returncode
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
