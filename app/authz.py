"""One place that decides "may this User do this to this item"."""
from __future__ import annotations


def is_admin(user) -> bool:
    return user["role"] == "admin"


def can_edit_post(user, post) -> bool:
    return is_admin(user) or post["author_id"] == user["id"]


def can_delete_post(user, post) -> bool:
    if is_admin(user):
        return True
    return post["author_id"] == user["id"] and post["status"] == "draft"


def can_edit_slug(user, post) -> bool:
    """Admin always; an Editor only while the Slug is not locked."""
    return is_admin(user) or not post["slug_locked"]


def can_unlock_slug(user) -> bool:
    return is_admin(user)


def can_edit_page(user, page) -> bool:
    """The Admin, or the one Editor the Page is assigned to."""
    return is_admin(user) or (page["assigned_editor_id"] is not None
                              and page["assigned_editor_id"] == user["id"])

