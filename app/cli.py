"""The `cms` command: serve, publish, deploy.

    uv run cms serve      # admin console + public preview at http://localhost:8000
    uv run cms publish    # render site/ from published content
    uv run cms deploy     # push site/ to the gh-pages branch (Pages serves it)
    uv run cms create-admin EMAIL   # make an Admin; asks for the password
    uv run cms reset-password EMAIL # reset any User's password (hidden prompt)
"""
from __future__ import annotations

import argparse
import getpass
import sqlite3

from app import deploy, settings, users
from app.publish import DraftInOutput, render


def main(argv: list[str] | None = None, *, push=deploy.push_site,
         confirm=input) -> int:
    """`push` and `confirm` are seams: tests stub them so nothing touches gh-pages."""
    parser = argparse.ArgumentParser(prog="cms")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the admin console locally")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", default=True)
    sub.add_parser("publish", help="render site/ from published content")
    deploy_cmd = sub.add_parser("deploy", help="push site/ to gh-pages")
    deploy_cmd.add_argument("--message", default="Publish site")
    create = sub.add_parser("create-admin", help="create an Admin account")
    create.add_argument("email")
    create.add_argument("--name", default="Admin", help="display name")
    reset = sub.add_parser("reset-password",
                           help="reset a User's password (works for the Admin)")
    reset.add_argument("email")
    args = parser.parse_args(argv)

    if args.command == "reset-password":
        users.init_db(settings.DATABASE_PATH)
        target = users.get_user_by_email(settings.DATABASE_PATH, args.email)
        if target is None:
            print(f"No user with the email {args.email}.")
            return 1
        print(f"Passwords must be at least {users.MIN_PASSWORD} characters.")
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("New password again: "):
            print("The passwords did not match; nothing was changed.")
            return 1
        problem = users.password_problem(password)
        if problem:
            print(f"{problem} Nothing was changed.")
            return 1
        users.set_password(settings.DATABASE_PATH, target["id"], password)
        print(f"Reset the password for {target['email']}.")
        return 0

    if args.command == "create-admin":
        print(f"Passwords must be at least {users.MIN_PASSWORD} characters.")
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Password again: "):
            print("The passwords did not match; nothing was created.")
            return 1
        users.init_db(settings.DATABASE_PATH)
        try:
            users.create_user(settings.DATABASE_PATH, email=args.email,
                              password=password, role="admin",
                              display_name=args.name)
        except ValueError as exc:
            print(f"{exc} Nothing was created.")
            return 1
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
        try:
            out, items = render()
        except DraftInOutput as exc:
            print(exc)
            return 1
        print("Rendered:")
        for item in items:
            print(f"  - {item}")
        print(f"Wrote {out}. Preview it with:  python3 -m http.server -d {out} 8001")
        return 0

    if args.command == "deploy":
        if not settings.SITE.exists():
            print("site/ does not exist yet — run `uv run cms publish` first.")
            return 1
        bad = deploy.root_absolute_files(settings.SITE)
        if bad:
            print("Refusing to deploy: root-absolute paths (href=\"/...\") in "
                  + ", ".join(str(b) for b in bad)
                  + ". Run `uv run cms publish` again.")
            return 1
        if confirm("Push site/ to gh-pages and make it Live? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Not deployed. Nothing was pushed.")
            return 0
        code = push(settings.SITE, args.message)
        if code != 0:
            print("The push failed, so nothing was recorded as deployed.")
            return code
        deploy.record_deploy(settings.DATABASE_PATH)
        print("Pushed to gh-pages. In GitHub: Settings -> Pages -> Deploy from a "
              "branch -> gh-pages / root. It can take up to 10 minutes to appear.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
