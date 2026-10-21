"""Login and logout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import users
from app.ratelimit import login_limiter
from app.security import csrf_token, start_session, verify_csrf
from app.templating import templates

router = APIRouter()

REFUSAL = "Invalid email or password."
LOCKOUT = "Too many failed attempts. Try again in 15 minutes."


def render_login(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request, "admin/login.html",
        {"title": "Log in", "csrf_token": csrf_token(request), "error": error})


@router.get("/login")
def login_form(request: Request):
    return render_login(request)


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login(request: Request, email: str = Form(""), password: str = Form("")):
    if login_limiter.is_locked(email):
        response = render_login(request, LOCKOUT)
        response.status_code = 429
        return response
    user = users.authenticate(request.app.state.database, email, password)
    if user is None:
        login_limiter.record_failure(email)
        return render_login(request, REFUSAL)
    start_session(request, user["id"])
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
