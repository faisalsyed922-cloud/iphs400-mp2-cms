"""The dashboard and the content list."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app import authz, content, users
from app.security import csrf_token, current_user
from app.templating import templates

router = APIRouter()
RECENT = 5


def can_edit_item(user, item) -> bool:
    if item["kind"] == "post":
        return authz.can_edit_post(user, {"author_id": item["owner_id"]})
    return authz.can_edit_page(user, {"assigned_editor_id": item["owner_id"]})


@router.get("/admin", name="admin_home")
def dashboard(request: Request, user=Depends(current_user)):
    db = request.app.state.database
    items = content.list_items(db)
    return templates.TemplateResponse(
        request, "admin/dashboard.html",
        {"title": "Dashboard", "user": user, "csrf_token": csrf_token(request),
         "pending": [i for i in items if i["pending"]],
         "drafts": [i for i in items if i["status"] == "draft"],
         "recent": [i for i in items if i["owner_id"] == user["id"]][:RECENT],
         "unassigned": content.unassigned_pages(db) if authz.is_admin(user) else None,
         "can_edit": can_edit_item, "is_admin": authz.is_admin(user)})


@router.get("/admin/content", name="content_list")
def content_list(request: Request, user=Depends(current_user), status: str = "",
                 type: str = "", author: str = "", mine: str = ""):
    db = request.app.state.database
    owner_id = user["id"] if mine else (int(author) if author.isascii() and author.isdigit() else None)
    return templates.TemplateResponse(
        request, "admin/content.html",
        {"title": "Content", "user": user, "csrf_token": csrf_token(request),
         "items": content.list_items(db, status=status, kind=type, owner_id=owner_id),
         "authors": users.list_users(db), "can_edit": can_edit_item,
         "filters": {"status": status, "type": type, "author": author, "mine": mine}})
