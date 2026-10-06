"""T08: dashboard and content list, tested through the HTTP app."""
import re
import sqlite3

import pytest
from conftest import token_from

from app import deploy, users


def csrf(c):
    return token_from(c.get("/admin").text)


def make_post(c, title, action="save"):
    r = c.post("/admin/posts", data={"title": title, "body": "x", "action": action,
                                     "csrf_token": csrf(c)}, follow_redirects=False)
    assert r.status_code == 303, r.text
    return int(re.search(r"/posts/(\d+)", r.headers["location"]).group(1))


def make_page(c, title, action="save", **extra):
    r = c.post("/admin/pages", data={"title": title, "body": "x", "action": action,
                                     "csrf_token": csrf(c), **extra},
               follow_redirects=False)
    assert r.status_code == 303, r.text
    return int(re.search(r"/pages/(\d+)", r.headers["location"]).group(1))


def section(html, name):
    """The HTML of one dashboard section, marked data-section="name"."""
    m = re.search(rf'<section data-section="{name}".*?</section>', html, re.S)
    return m.group(0) if m else ""


def set_updated(db_path, table, item_id, stamp):
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"update {table} set updated_at=? where id=?", (stamp, item_id))


@pytest.fixture
def other_editor(db_path, make_client):
    users.create_user(db_path, email="other@example.test", password="other-editor-pw",
                      role="editor", display_name="Other Editor")
    c = make_client()
    c.post("/login", data={"email": "other@example.test", "password": "other-editor-pw",
                           "csrf_token": token_from(c.get("/login").text)})
    return c


# --- access ----------------------------------------------------------------
@pytest.mark.parametrize("path", ["/admin", "/admin/content"])
def test_anonymous_is_redirected(client, path):
    r = client.get(path, follow_redirects=False)
    assert r.status_code in (302, 303) and r.headers["location"].endswith("/login")


def test_pages_are_readable_at_phone_width(client_as):
    for path in ("/admin", "/admin/content"):
        assert 'name="viewport"' in client_as("editor").get(path).text


# --- dashboard -------------------------------------------------------------
def test_dashboard_order_is_pending_then_drafts_then_recent(client_as):
    c = client_as("editor")
    make_post(c, "Live-ish post", action="publish")
    make_post(c, "Half written")
    html = c.get("/admin").text
    order = [html.index(f'data-section="{s}"') for s in ("pending", "drafts", "recent")]
    assert order == sorted(order)
    assert "Live-ish post" in section(html, "pending")
    assert "Half written" not in section(html, "pending")
    assert "Half written" in section(html, "drafts")


def test_never_deployed_published_item_is_pending_but_drafts_are_not(client_as):
    c = client_as("admin")
    make_page(c, "About", action="publish")
    make_page(c, "Secret", action="save")
    pending = section(c.get("/admin").text, "pending")
    assert "About" in pending and "Secret" not in pending


def test_deploy_clears_pending_and_later_edit_brings_it_back(client_as, db_path):
    c = client_as("editor")
    pid = make_post(c, "News item", action="publish")
    deploy.record_deploy(db_path)
    set_updated(db_path, "posts", pid, "2000-01-01T00:00:00+00:00")
    assert "News item" not in section(c.get("/admin").text, "pending")
    set_updated(db_path, "posts", pid, "2999-01-01T00:00:00+00:00")
    assert "News item" in section(c.get("/admin").text, "pending")


def test_recent_shows_only_my_items(client_as, other_editor):
    other_editor.post("/admin/posts", data={"title": "Theirs", "body": "x",
                      "csrf_token": csrf(other_editor)})
    c = client_as("editor")
    make_post(c, "Mine one")
    recent = section(c.get("/admin").text, "recent")
    assert "Mine one" in recent and "Theirs" not in recent


def test_unassigned_pages_section_is_admin_only(client_as):
    admin = client_as("admin")
    make_page(admin, "History")
    assert "History" in section(admin.get("/admin").text, "unassigned")
    editor = client_as("editor")
    assert section(editor.get("/admin").text, "unassigned") == ""


# --- content list ----------------------------------------------------------
def test_list_shows_posts_and_pages_with_status_badges(client_as):
    c = client_as("admin")
    make_post(c, "A post", action="publish")
    make_page(c, "A page")
    html = c.get("/admin/content").text
    assert "A post" in html and "A page" in html
    assert 'class="badge badge-published"' in html
    assert 'class="badge badge-draft"' in html


def test_filters_by_status_type_and_author(client_as, other_editor):
    other_editor.post("/admin/posts", data={"title": "Other draft", "body": "x",
                      "csrf_token": csrf(other_editor)})
    c = client_as("admin")
    make_post(c, "Admin published", action="publish")
    make_page(c, "Admin page")
    get = lambda q: c.get("/admin/content" + q).text  # noqa: E731
    assert "Admin page" not in get("?type=post")
    assert "Admin published" not in get("?type=page")
    assert "Other draft" not in get("?status=published")
    assert "Admin published" not in get("?status=draft")
    other_id = users.get_user_by_email(c.app.state.database, "other@example.test")["id"]
    by_author = get(f"?author={other_id}")
    assert "Other draft" in by_author and "Admin published" not in by_author


def test_mine_shortcut_shows_only_my_items(client_as, other_editor):
    other_editor.post("/admin/posts", data={"title": "Theirs", "body": "x",
                      "csrf_token": csrf(other_editor)})
    c = client_as("editor")
    make_post(c, "Mine")
    html = c.get("/admin/content?mine=1").text
    assert "Mine" in html and "Theirs" not in html


def test_list_has_no_categories_tags_or_bulk_actions(client_as):
    html = client_as("admin").get("/admin/content").text.lower()
    for word in ("categor", "tags", "bulk", 'type="checkbox"'):
        assert word not in html


def test_other_peoples_rows_have_no_edit_link_for_editors(client_as, other_editor):
    other_editor.post("/admin/posts", data={"title": "Theirs", "body": "x",
                      "csrf_token": csrf(other_editor)})
    admin = client_as("admin")
    make_page(admin, "Unassigned page")
    html = client_as("editor").get("/admin/content").text
    assert "Theirs" in html and "Unassigned page" in html
    assert "/admin/posts/1" not in html and "/admin/pages/1" not in html


def test_own_rows_and_assigned_pages_are_editable_for_editors(client_as):
    admin = client_as("admin")
    editor_id = users.get_user_by_email(admin.app.state.database,
                                        "editor@example.test")["id"]
    pid = make_page(admin, "Assigned", assigned_editor_id=str(editor_id))
    c = client_as("editor")
    post_id = make_post(c, "Own")
    html = c.get("/admin/content").text
    assert f"/admin/pages/{pid}" in html and f"/admin/posts/{post_id}" in html


def test_items_changed_since_last_deploy_are_marked(client_as, db_path):
    c = client_as("editor")
    pid = make_post(c, "Old", action="publish")
    deploy.record_deploy(db_path)
    set_updated(db_path, "posts", pid, "2000-01-01T00:00:00+00:00")
    assert "changed since last Deploy" not in c.get("/admin/content").text
    make_post(c, "Fresh")
    assert "changed since last Deploy" in c.get("/admin/content").text
