"""The FastAPI application.

T00 (already done): the admin console answers at /admin and the public site
answers at /. That is the whole skeleton — it exists so you can prove the stack
runs before you build anything on it.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app import posts, settings, users
from app.routes import auth, posts as posts_routes
from app.security import SESSION_SECONDS, LoginRequired, csrf_token, current_user
from app.templating import templates


def create_app(database: Path | None = None) -> FastAPI:
    app = FastAPI(title="IPHS 400 MP2 CMS")
    app.state.database = Path(database or settings.DATABASE_PATH)
    users.init_db(app.state.database)
    posts.init_posts(app.state.database)
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                       max_age=SESSION_SECONDS, same_site="lax")

    @app.exception_handler(LoginRequired)
    def send_to_login(request: Request, exc: LoginRequired):
        return RedirectResponse("/login", status_code=303)

    app.include_router(auth.router)
    app.include_router(posts_routes.router)

    @app.get("/admin")
    def admin_home(request: Request, user=Depends(current_user)):
        return templates.TemplateResponse(
            request, "admin/hello.html",
            {"title": "Admin", "user": user, "csrf_token": csrf_token(request)}
        )

    @app.get("/")
    def public_home(request: Request):
        return templates.TemplateResponse(
            request, "public/home.html",
            {"title": settings.SITE_TITLE, "items": []},
        )

    # Your ticket work plugs in here, e.g.
    #   from app.routes import posts
    #   app.include_router(posts.router)
    return app


app = create_app()
