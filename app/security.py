"""Sessions, CSRF protection and the login requirement for admin routes."""
from __future__ import annotations

import secrets

from fastapi import HTTPException, Request

from app import users

SESSION_SECONDS = 8 * 60 * 60


class LoginRequired(Exception):
    """Raised for an anonymous (or Deactivated) visitor; becomes a redirect."""


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = request.session["csrf"] = secrets.token_urlsafe(32)
    return token


async def verify_csrf(request: Request) -> None:
    """Dependency for every state-changing route: reject a missing/wrong token."""
    form = await request.form()
    sent = str(form.get("csrf_token", ""))
    expected = request.session.get("csrf", "")
    if not expected or not secrets.compare_digest(sent, expected):
        raise HTTPException(status_code=403, detail="Missing or invalid CSRF token")


def start_session(request: Request, user_id: int) -> None:
    request.session.clear()
    request.session["user_id"] = user_id
    request.session["csrf"] = secrets.token_urlsafe(32)


def current_user(request: Request):
    """Dependency: the logged-in, active user, or redirect to login."""
    user_id = request.session.get("user_id")
    user = users.get_user(request.app.state.database, user_id) if user_id else None
    if user is None or not user["is_active"]:
        request.session.clear()
        raise LoginRequired
    return user
