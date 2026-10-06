"""Sessions, CSRF protection and the login requirement for admin routes."""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, Request
from itsdangerous import SignatureExpired, TimestampSigner
from starlette.middleware.sessions import SessionMiddleware

from app import users

SESSION_SECONDS = 8 * 60 * 60
# How far in the future a validly signed session may look. A wall clock that
# steps backwards (WSL2 and VM clock syncs do) would otherwise log everyone out.
CLOCK_SKEW_SECONDS = 5 * 60


class SkewTolerantSigner(TimestampSigner):
    """itsdangerous rejects a cookie stamped even 1s ahead of the clock; allow a little."""

    def unsign(self, signed_value, max_age=None, return_timestamp=False):
        try:
            return super().unsign(signed_value, max_age=max_age,
                                  return_timestamp=return_timestamp)
        except SignatureExpired as exc:
            signed = exc.date_signed
            # Only raised after the signature itself verified.
            ahead = signed.timestamp() - self.get_timestamp() if signed else 0
            if not 0 < ahead <= CLOCK_SKEW_SECONDS:
                raise
            value = exc.payload
            return (value, signed) if return_timestamp else value


class SkewTolerantSessionMiddleware(SessionMiddleware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signer = SkewTolerantSigner(str(kwargs.get("secret_key") or args[1]))


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


class PasswordChangeRequired(Exception):
    """A User on a temporary password must set their own first."""


def logged_in_user(request: Request):
    """Dependency: the logged-in, active user, or redirect to login."""
    user_id = request.session.get("user_id")
    user = users.get_user(request.app.state.database, user_id) if user_id else None
    if user is None or not user["is_active"]:
        request.session.clear()
        raise LoginRequired
    return user


def current_user(user=Depends(logged_in_user)):
    """Like logged_in_user, but a temporary password blocks everything else."""
    if user["must_change_password"]:
        raise PasswordChangeRequired
    return user


class AdminRequired(Exception):
    """Raised for a logged-in non-Admin on an admin-only URL; becomes a 403 page."""


def require_admin(user=Depends(current_user)):
    """Dependency for every admin-only route. Anonymous users redirect first."""
    if user["role"] != "admin":
        raise AdminRequired
    return user
