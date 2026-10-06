"""Posts: list, create, edit, publish, preview, delete."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import authz, posts, users
from app.markdown import render_markdown
from app.security import csrf_token, current_user, verify_csrf
from app.templating import templates

router = APIRouter(prefix="/admin/posts")
guarded = [Depends(current_user), Depends(verify_csrf)]

ACTIONS = {"save", "publish", "draft"}


def load_post(request: Request, user, post_id: int, allowed) -> dict:
    """Fetch a Post the current User is allowed to act on, or 404/403."""
    post = posts.get_post(request.app.state.database, post_id)
    if post is None:
        raise HTTPException(404, "No such post.")
    if not allowed(user, post):
        raise HTTPException(403, "You can only change your own Posts.")
    return post


def render_form(request: Request, user, *, post=None, form=None, error=None,
                status_code=200):
    if form is None:
        form = ({"title": post["title"], "slug": post["slug"], "body": post["body"]}
                if post else {})
    return templates.TemplateResponse(
        request, "admin/post_form.html",
        {"title": "Edit post" if post else "New post", "user": user, "post": post,
         "form": form, "error": error, "csrf_token": csrf_token(request),
         "byline": posts.byline(post) if post and post["published_at"] else None,
         "can_edit_slug": authz.can_edit_slug(user, post) if post else True,
         "can_unlock_slug": bool(post and post["slug_locked"]
                                 and authz.can_unlock_slug(user)),
         "can_delete": bool(post and authz.can_delete_post(user, post))},
        status_code=status_code)


@router.get("")
def list_view(request: Request, user=Depends(current_user)):
    return templates.TemplateResponse(
        request, "admin/posts.html",
        {"title": "Posts", "user": user, "csrf_token": csrf_token(request),
         "posts": posts.list_posts(request.app.state.database),
         "can_edit": authz.can_edit_post})


@router.get("/new")
def new_form(request: Request, user=Depends(current_user)):
    return render_form(request, user)


@router.post("/preview", dependencies=guarded)
def preview(request: Request, user=Depends(current_user), title: str = Form(""),
            body: str = Form(""), post_id: int | None = Form(None)):
    author = user
    byline = None
    if post_id is not None:
        post = load_post(request, user, post_id, authz.can_edit_post)
        author = users.get_user(request.app.state.database, post["author_id"])
        byline = posts.byline(post) if post["published_at"] else None
    if byline is None:
        byline = posts.format_byline(author["display_name"], author["title"],
                                     author["term"])
    return templates.TemplateResponse(
        request, "admin/preview.html",
        {"title": title or "Untitled", "html": render_markdown(body),
         "byline": byline})


@router.post("", dependencies=guarded)
def create(request: Request, user=Depends(current_user), title: str = Form(""),
           slug: str = Form(""), body: str = Form(""), action: str = Form("save")):
    form = {"title": title, "slug": slug, "body": body}
    if not title.strip():
        return render_form(request, user, form=form, error="A Post needs a title.",
                           status_code=400)
    try:
        post_id = posts.create_post(
            request.app.state.database, author=user, title=title.strip(),
            slug=posts.slugify(slug) if slug.strip() else "", body=body,
            publish=action == "publish")
    except posts.DuplicateSlug:
        return render_form(request, user, form=form, status_code=400,
                           error="That Slug is already used by another Post.")
    return RedirectResponse(f"/admin/posts/{post_id}", status_code=303)


@router.get("/{post_id:int}")
def edit_form(request: Request, post_id: int, user=Depends(current_user)):
    post = load_post(request, user, post_id, authz.can_edit_post)
    return render_form(request, user, post=post)


@router.post("/{post_id:int}", dependencies=guarded)
def save(request: Request, post_id: int, user=Depends(current_user),
         title: str = Form(""), slug: str = Form(""), body: str = Form(""),
         action: str = Form("save")):
    post = load_post(request, user, post_id, authz.can_edit_post)
    if action not in ACTIONS:
        raise HTTPException(400, "Unknown action.")
    form = {"title": title, "slug": slug, "body": body}
    if not title.strip():
        return render_form(request, user, post=post, form=form, status_code=400,
                           error="A Post needs a title.")
    new_slug = None
    if authz.can_edit_slug(user, post):
        new_slug = posts.slugify(slug) if slug.strip() else post["slug"]
    try:
        posts.update_post(request.app.state.database, post_id, title=title.strip(),
                          body=body, slug=new_slug, action=action)
    except posts.DuplicateSlug:
        return render_form(request, user, post=post, form=form, status_code=400,
                           error="That Slug is already used by another Post.")
    return RedirectResponse(f"/admin/posts/{post_id}", status_code=303)


@router.post("/{post_id:int}/unlock-slug", dependencies=guarded)
def unlock_slug(request: Request, post_id: int, user=Depends(current_user)):
    if not authz.can_unlock_slug(user):
        raise HTTPException(403, "Only the Admin can unlock a Slug.")
    if posts.get_post(request.app.state.database, post_id) is None:
        raise HTTPException(404, "No such post.")
    posts.unlock_slug(request.app.state.database, post_id)
    return RedirectResponse(f"/admin/posts/{post_id}", status_code=303)


@router.post("/{post_id:int}/delete", dependencies=guarded)
def delete(request: Request, post_id: int, user=Depends(current_user)):
    load_post(request, user, post_id, authz.can_delete_post)
    posts.delete_post(request.app.state.database, post_id)
    return RedirectResponse("/admin/posts", status_code=303)
