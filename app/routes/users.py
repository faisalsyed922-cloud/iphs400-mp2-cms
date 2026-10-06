"""Admin-only user management. Every route needs the Admin role."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import users
from app.security import csrf_token, require_admin, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/admin/users")
guarded = [Depends(require_admin), Depends(verify_csrf)]

LAST_ADMIN = ("This is the last active Admin. Promote a successor to Admin "
              "first, then try again.")


def render(request: Request, template: str, status_code: int = 200, **ctx):
    return templates.TemplateResponse(
        request, template,
        {"csrf_token": csrf_token(request), "roles": users.ROLES,
         "min_password": users.MIN_PASSWORD, **ctx}, status_code=status_code)


def load_user(request: Request, user_id: int):
    found = users.get_user(request.app.state.database, user_id)
    if found is None:
        raise HTTPException(404, "No such user.")
    return found


@router.get("")
def users_list(request: Request, user=Depends(require_admin), notice: str = ""):
    db = request.app.state.database
    return render(request, "admin/users.html", title="Users", user=user,
                  users=users.list_users(db), notice=notice,
                  contact_line=users.get_setting(db, "contact_line"))


@router.get("/new")
def user_new(request: Request, user=Depends(require_admin)):
    return render(request, "admin/user_new.html", title="New user", user=user,
                  form={"role": "editor"}, error=None)


@router.post("", dependencies=guarded)
def create(request: Request, user=Depends(require_admin),
           email: str = Form(""), display_name: str = Form(""),
           title: str = Form(""), term: str = Form(""), role: str = Form("editor"),
           password: str = Form("")):
    form = {"email": email, "display_name": display_name, "title": title,
            "term": term, "role": role}

    def fail(message: str):
        return render(request, "admin/user_new.html", 400, title="New user",
                      user=user, form=form, error=message)

    if not email.strip() or not display_name.strip():
        return fail("Email and display name are required.")
    if role not in users.ROLES:
        return fail("Choose Admin or Editor.")
    if len(password) < users.MIN_PASSWORD:
        return fail(f"The password must be at least {users.MIN_PASSWORD} characters.")
    try:
        users.create_user(request.app.state.database, email=email,
                          password=password, role=role,
                          display_name=display_name.strip(), title=title.strip(),
                          term=term.strip())
    except sqlite3.IntegrityError:
        return fail("That email already has an account.")
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/contact", dependencies=guarded)
def save_contact(request: Request, contact_line: str = Form("")):
    users.set_setting(request.app.state.database, "contact_line",
                      contact_line.strip())
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/{user_id:int}")
def user_edit(request: Request, user_id: int, user=Depends(require_admin)):
    target = load_user(request, user_id)
    return render(request, "admin/user_edit.html", title="Edit user", user=user,
                  target=target, error=None)


@router.post("/{user_id:int}", dependencies=guarded)
def save(request: Request, user_id: int, user=Depends(require_admin),
         display_name: str = Form(""), title: str = Form(""), term: str = Form(""),
         role: str = Form("editor")):
    target = load_user(request, user_id)
    error = None
    if not display_name.strip():
        error = "A display name is required."
    elif role not in users.ROLES:
        error = "Choose Admin or Editor."
    else:
        try:
            users.update_user(request.app.state.database, user_id,
                              display_name=display_name.strip(),
                              title=title.strip(), term=term.strip(), role=role)
        except users.LastAdmin:
            error = LAST_ADMIN
    if error:
        return render(request, "admin/user_edit.html", 400, title="Edit user",
                      user=user, target=target, error=error)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/{user_id:int}/deactivate", dependencies=guarded)
def deactivate(request: Request, user_id: int, user=Depends(require_admin)):
    target = load_user(request, user_id)
    try:
        users.deactivate_user(request.app.state.database, user_id)
    except users.LastAdmin:
        return render(request, "admin/user_edit.html", 400, title="Edit user",
                      user=user, target=target, error=LAST_ADMIN)
    return RedirectResponse("/admin/users", status_code=303)
