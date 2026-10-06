"""Pages: list, create, edit, publish, preview, delete. Navigation and the Home
flag are Admin-only; an Editor works only on the Page assigned to them."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import authz, pages, posts
from app.markdown import render_markdown
from app.publish import navigation
from app.security import csrf_token, current_user, require_admin, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/admin/pages")
guarded = [Depends(current_user), Depends(verify_csrf)]
admin_guarded = [Depends(require_admin), Depends(verify_csrf)]

ACTIONS = {"save", "publish", "draft"}
TAKEN = "That Slug is already used by another Page."


def load_page(request: Request, user, page_id: int, allowed=authz.can_edit_page):
    page = pages.get_page(request.app.state.database, page_id)
    if page is None:
        raise HTTPException(404, "No such page.")
    if not allowed(user, page):
        raise HTTPException(403, "You can only change the Page assigned to you.")
    return page


def render_form(request: Request, user, *, page=None, form=None, error=None,
                status_code=200):
    db = request.app.state.database
    if form is None:
        form = ({"title": page["title"], "slug": page["slug"], "body": page["body"],
                 "assigned_editor_id": page["assigned_editor_id"],
                 "show_in_nav": page["show_in_nav"], "nav_order": page["nav_order"],
                 "is_home": page["is_home"]} if page else {"nav_order": 0})
    return templates.TemplateResponse(
        request, "admin/page_form.html",
        {"title": "Edit page" if page else "New page", "user": user, "page": page,
         "form": form, "error": error, "csrf_token": csrf_token(request),
         "is_admin": authz.is_admin(user), "editors": pages.active_editors(db),
         "can_edit_slug": authz.can_edit_slug(user, page) if page else True,
         "can_unlock_slug": bool(page and page["slug_locked"] and authz.is_admin(user)),},
        status_code=status_code)


def admin_fields(request: Request, assigned_editor_id: str, show_in_nav: str,
                 nav_order: str, is_home: str):
    """Parse the Admin-only fields; return (fields, error)."""
    editor = None
    if assigned_editor_id.strip():
        if (not assigned_editor_id.strip().isdigit() or not pages.is_assignable(
                request.app.state.database, int(assigned_editor_id))):
            return None, "Choose an active Editor, or leave the Page unassigned."
        editor = int(assigned_editor_id)
    try:
        order = int(nav_order or 0)
    except ValueError:
        return None, "The Navigation order must be a whole number."
    return {"assigned_editor_id": editor, "show_in_nav": bool(show_in_nav),
            "nav_order": order, "is_home": bool(is_home)}, None


@router.get("")
def pages_list(request: Request, user=Depends(current_user)):
    return templates.TemplateResponse(
        request, "admin/pages.html",
        {"title": "Pages", "user": user, "csrf_token": csrf_token(request),
         "pages": pages.list_pages(request.app.state.database),
         "can_edit": authz.can_edit_page, "is_admin": authz.is_admin(user)})


@router.get("/new")
def new_form(request: Request, user=Depends(require_admin)):
    return render_form(request, user)


@router.post("/preview", dependencies=guarded)
def preview(request: Request, user=Depends(current_user), title: str = Form(""),
            body: str = Form(""), page_id: int | None = Form(None)):
    if page_id is not None:
        load_page(request, user, page_id)
    elif not authz.is_admin(user):
        raise HTTPException(403, "Only the Admin can create Pages.")
    return templates.TemplateResponse(
        request, "admin/preview.html",
        {"title": title or "Untitled", "html": render_markdown(body), "byline": None,
         "nav_links": navigation(request.app.state.database), "nav_preview": True})


@router.post("", dependencies=admin_guarded)
def create(request: Request, user=Depends(require_admin), title: str = Form(""),
           slug: str = Form(""), body: str = Form(""), action: str = Form("save"),
           assigned_editor_id: str = Form(""), show_in_nav: str = Form(""),
           nav_order: str = Form("0"), is_home: str = Form("")):
    form = {"title": title, "slug": slug, "body": body,
            "assigned_editor_id": assigned_editor_id, "show_in_nav": show_in_nav,
            "nav_order": nav_order, "is_home": is_home}
    fields, error = admin_fields(request, assigned_editor_id, show_in_nav, nav_order,
                                 is_home)
    if not title.strip():
        error = "A Page needs a title."
    if error:
        return render_form(request, user, form=form, error=error, status_code=400)
    try:
        page_id = pages.create_page(
            request.app.state.database, title=title.strip(),
            slug=posts.slugify(slug) if slug.strip() else "", body=body,
            publish=action == "publish", **fields)
    except pages.DuplicateSlug:
        return render_form(request, user, form=form, error=TAKEN, status_code=400)
    return RedirectResponse(f"/admin/pages/{page_id}", status_code=303)


@router.get("/{page_id:int}")
def edit_form(request: Request, page_id: int, user=Depends(current_user)):
    return render_form(request, user, page=load_page(request, user, page_id))


@router.post("/{page_id:int}", dependencies=guarded)
def save(request: Request, page_id: int, user=Depends(current_user),
         title: str = Form(""), slug: str = Form(""), body: str = Form(""),
         action: str = Form("save"), assigned_editor_id: str = Form(""),
         show_in_nav: str = Form(""), nav_order: str = Form("0"),
         is_home: str = Form("")):
    page = load_page(request, user, page_id)
    if action not in ACTIONS:
        raise HTTPException(400, "Unknown action.")
    form = {"title": title, "slug": slug, "body": body,
            "assigned_editor_id": assigned_editor_id, "show_in_nav": show_in_nav,
            "nav_order": nav_order, "is_home": is_home}
    error = None
    fields = None
    if authz.is_admin(user):
        fields, error = admin_fields(request, assigned_editor_id, show_in_nav,
                                     nav_order, is_home)
        if fields and page["is_home"]:
            fields["is_home"] = True  # the flag only ever moves, never disappears
    if not title.strip():
        error = "A Page needs a title."
    if error:
        return render_form(request, user, page=page, form=form, error=error,
                           status_code=400)
    new_slug = None
    if authz.can_edit_slug(user, page):
        new_slug = posts.slugify(slug) if slug.strip() else page["slug"]
    try:
        pages.update_page(request.app.state.database, page_id, title=title.strip(),
                          body=body, slug=new_slug, action=action,
                          admin_fields=fields)
    except pages.DuplicateSlug:
        return render_form(request, user, page=page, form=form, error=TAKEN,
                           status_code=400)
    return RedirectResponse(f"/admin/pages/{page_id}", status_code=303)


@router.post("/{page_id:int}/unlock-slug", dependencies=admin_guarded)
def unlock_slug(request: Request, page_id: int, user=Depends(require_admin)):
    load_page(request, user, page_id)
    pages.unlock_slug(request.app.state.database, page_id)
    return RedirectResponse(f"/admin/pages/{page_id}", status_code=303)


@router.post("/{page_id:int}/delete", dependencies=admin_guarded)
def delete(request: Request, page_id: int, user=Depends(require_admin)):
    page = load_page(request, user, page_id)
    try:
        pages.delete_page(request.app.state.database, page_id)
    except pages.HomePage:
        return render_form(request, user, page=page, status_code=400,
                           error="This is the Home page. Flag another Page as Home "
                                 "first, then delete this one.")
    return RedirectResponse("/admin/pages", status_code=303)
