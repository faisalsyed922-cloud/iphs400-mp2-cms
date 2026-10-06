"""Login and logout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import users
from app.security import csrf_token, start_session, verify_csrf
from app.templating import templates

router = APIRouter()

REFUSAL = "Invalid email or password."


def render_login(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        request, "admin/login.html",
        {"title": "Log in", "csrf_token": csrf_token(request), "error": error})


@router.get("/login")
def login_form(request: Request):
    return render_login(request)


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login(request: Request, email: str = Form(""), password: str = Form("")):
    user = users.authenticate(request.app.state.database, email, password)
    if user is None:
        return render_login(request, REFUSAL)
    start_session(request, user["id"])
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
