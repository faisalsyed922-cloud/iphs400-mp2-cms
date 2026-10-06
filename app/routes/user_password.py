"""A User changing their own password (also the forced change after a reset)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import users
from app.security import csrf_token, logged_in_user, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/user")


def render(request: Request, user, error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request, "admin/change_password.html",
        {"title": "Change password", "user": user, "error": error,
         "csrf_token": csrf_token(request), "min_password": users.MIN_PASSWORD,
         "forced": bool(user["must_change_password"])}, status_code=status_code)


@router.get("/password")
def password_form(request: Request, user=Depends(logged_in_user)):
    return render(request, user)


@router.post("/password", dependencies=[Depends(verify_csrf)])
def change_password(request: Request, user=Depends(logged_in_user),
                    current_password: str = Form(""), new_password: str = Form(""),
                    confirm_password: str = Form("")):
    def fail(message: str):
        return render(request, user, message, 400)

    if not users.verify_password(user, current_password):
        return fail("Your current password is not correct.")
    problem = users.password_problem(new_password)
    if problem:
        return fail(problem)
    if new_password != confirm_password:
        return fail("The new passwords do not match.")
    if new_password == current_password:
        return fail("Choose a password different from the current one.")
    users.set_password(request.app.state.database, user["id"], new_password)
    return RedirectResponse("/admin", status_code=303)
