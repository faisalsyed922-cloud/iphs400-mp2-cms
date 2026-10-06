"""T07: Pages, Assigned editor and Navigation, tested through the HTTP app."""
import re
import sqlite3

import pytest
from conftest import token_from

from app import users

EDITOR_ID = 2


def csrf(c):
    return token_from(c.get("/admin").text)


def save_page(c, title="About", slug="", body="About us.", action="save",
              page_id=None, **extra):
    path = f"/admin/pages/{page_id}" if page_id else "/admin/pages"
    data = {"title": title, "slug": slug, "body": body, "action": action,
            "csrf_token": csrf(c), **extra}
    return c.post(path, data=data, follow_redirects=False)


def page_id_of(response):
    assert response.status_code == 303, response.text
    return int(re.search(r"/admin/pages/(\d+)", response.headers["location"]).group(1))


def page_post(c, page_id, suffix, **data):
    return c.post(f"/admin/pages/{page_id}{suffix}",
                  data={"csrf_token": csrf(c), **data}, follow_redirects=False)


def row(db_path, page_id, column):
    return sqlite3.connect(db_path).execute(
        f"select {column} from pages where id=?", (page_id,)).fetchone()[0]


@pytest.fixture
def other_editor(db_path, make_client):
    users.create_user(db_path, email="other@example.test", password="other-editor-pw",
                      role="editor", display_name="Other Editor")
    c = make_client()
    c.post("/login", data={"email": "other@example.test", "password": "other-editor-pw",
                           "csrf_token": token_from(c.get("/login").text)})
    return c


# --- creating and permissions ----------------------------------------------

def test_admin_creates_a_page_with_all_fields(client_as, db_path):
    a = client_as("admin")
    pid = page_id_of(save_page(a, title="Community Service", body="We serve.",
                               assigned_editor_id=str(EDITOR_ID), show_in_nav="on",
                               nav_order="2"))
    html = a.get(f"/admin/pages/{pid}").text
    assert "community-service" in html and "Draft" in html
    assert row(db_path, pid, "assigned_editor_id") == EDITOR_ID
    assert row(db_path, pid, "show_in_nav") == 1
    assert row(db_path, pid, "nav_order") == 2


def test_editor_cannot_create_or_delete_pages(client_as, db_path):
    a, e = client_as("admin"), client_as("editor")
    pid = page_id_of(save_page(a, assigned_editor_id=str(EDITOR_ID)))
    assert e.get("/admin/pages/new", follow_redirects=False).status_code == 403
    assert save_page(e, title="Sneaky").status_code == 403
    assert page_post(e, pid, "/delete").status_code == 403
    assert row(db_path, pid, "id") == pid


def test_duplicate_page_slug_refused_but_post_slug_is_independent(client_as):
    a = client_as("admin")
    save_page(a, title="History")
    r = save_page(a, title="Other", slug="history")
    assert r.status_code == 400 and "already used" in r.text
    # a Post may share a Slug with a Page: uniqueness is within each kind
    token = token_from(a.get("/admin/posts/new").text)
    r = a.post("/admin/posts", data={"title": "History", "slug": "", "body": "x",
                                     "action": "save", "csrf_token": token},
               follow_redirects=False)
    assert r.status_code == 303


# --- Assigned editor -------------------------------------------------------

def test_only_assigned_editor_and_admin_can_edit(client_as, other_editor, db_path):
    a, e = client_as("admin"), client_as("editor")
    pid = page_id_of(save_page(a, assigned_editor_id=str(EDITOR_ID)))
    assert e.get(f"/admin/pages/{pid}").status_code == 200
    assert other_editor.get(f"/admin/pages/{pid}").status_code == 403
    assert save_page(other_editor, page_id=pid, title="Hacked").status_code == 403
    assert row(db_path, pid, "title") == "About"
    r = save_page(e, page_id=pid, title="About Us", body="New text")
    assert r.status_code == 303 and row(db_path, pid, "title") == "About Us"


def test_unassigned_page_is_admin_only(client_as):
    a, e = client_as("admin"), client_as("editor")
    pid = page_id_of(save_page(a))
    assert e.get(f"/admin/pages/{pid}").status_code == 403
    assert a.get(f"/admin/pages/{pid}").status_code == 200


def test_editor_cannot_change_assignment_navigation_or_home(client_as, db_path):
    a, e = client_as("admin"), client_as("editor")
    save_page(a, title="First")  # becomes Home automatically
    pid = page_id_of(save_page(a, title="Mine", assigned_editor_id=str(EDITOR_ID)))
    save_page(e, page_id=pid, title="Mine", assigned_editor_id="", show_in_nav="on",
              nav_order="9", is_home="on")
    assert row(db_path, pid, "assigned_editor_id") == EDITOR_ID
    assert row(db_path, pid, "show_in_nav") == 0
    assert row(db_path, pid, "nav_order") == 0
    assert row(db_path, pid, "is_home") == 0


def test_editor_form_hides_admin_controls(client_as):
    a, e = client_as("admin"), client_as("editor")
    pid = page_id_of(save_page(a, assigned_editor_id=str(EDITOR_ID)))
    html = e.get(f"/admin/pages/{pid}").text
    for name in ("assigned_editor_id", "show_in_nav", "nav_order", "is_home", "/delete"):
        assert name not in html
    assert "Mark Published" in html


def test_assigned_editor_can_publish_and_set_their_page_back_to_draft(client_as, db_path):
    a, e = client_as("admin"), client_as("editor")
    pid = page_id_of(save_page(a, assigned_editor_id=str(EDITOR_ID)))
    save_page(e, page_id=pid, action="publish")
    assert row(db_path, pid, "status") == "published"
    assert "Set back to Draft" in e.get(f"/admin/pages/{pid}").text
    assert save_page(e, page_id=pid, action="draft").status_code == 303
    assert row(db_path, pid, "status") == "draft"
    save_page(a, page_id=pid, action="publish")
    save_page(a, page_id=pid, action="draft")
    assert row(db_path, pid, "status") == "draft"


def test_other_editor_cannot_set_a_page_back_to_draft(client_as, other_editor, db_path):
    pid = page_id_of(save_page(client_as("admin"), assigned_editor_id=str(EDITOR_ID),
                               action="publish"))
    assert save_page(other_editor, page_id=pid, action="draft").status_code == 403
    assert row(db_path, pid, "status") == "published"


def test_other_editor_cannot_publish_a_page_by_direct_post(client_as, other_editor, db_path):
    pid = page_id_of(save_page(client_as("admin"), assigned_editor_id=str(EDITOR_ID)))
    assert save_page(other_editor, page_id=pid, action="publish").status_code == 403
    assert row(db_path, pid, "status") == "draft"


def test_assignee_must_be_an_active_editor(client_as, db_path):
    a = client_as("admin")
    r = save_page(a, assigned_editor_id="1")  # the Admin
    assert r.status_code == 400
    r = save_page(a, assigned_editor_id="999")
    assert r.status_code == 400


# --- Home flag -------------------------------------------------------------

def test_exactly_one_home_page_and_flagging_moves_it(client_as, db_path):
    a = client_as("admin")
    first = page_id_of(save_page(a, title="Welcome"))
    assert row(db_path, first, "is_home") == 1  # the first Page is Home
    second = page_id_of(save_page(a, title="Other", is_home="on"))
    assert row(db_path, second, "is_home") == 1 and row(db_path, first, "is_home") == 0
    save_page(a, page_id=second, title="Other")  # unticked: flag stays put
    assert row(db_path, second, "is_home") == 1
    total = sqlite3.connect(db_path).execute(
        "select count(*) from pages where is_home=1").fetchone()[0]
    assert total == 1


def test_home_page_cannot_be_deleted_while_others_exist(client_as, db_path):
    a = client_as("admin")
    home = page_id_of(save_page(a, title="Welcome"))
    other = page_id_of(save_page(a, title="Other"))
    assert page_post(a, home, "/delete").status_code == 400
    assert row(db_path, home, "id") == home
    assert page_post(a, other, "/delete").status_code == 303


# --- Slug lock -------------------------------------------------------------

def test_slug_locks_after_first_publish_and_admin_can_unlock(client_as, db_path):
    a, e = client_as("admin"), client_as("editor")
    pid = page_id_of(save_page(a, title="History", assigned_editor_id=str(EDITOR_ID)))
    save_page(e, page_id=pid, title="History", slug="the-past")  # allowed while unlocked
    assert row(db_path, pid, "slug") == "the-past"
    save_page(e, page_id=pid, title="History", slug="the-past", action="publish")
    save_page(e, page_id=pid, title="History", slug="changed")
    assert row(db_path, pid, "slug") == "the-past"
    assert page_post(e, pid, "/unlock-slug").status_code == 403
    page_post(a, pid, "/unlock-slug")
    save_page(a, page_id=pid, title="History", slug="changed")
    assert row(db_path, pid, "slug") == "changed"


# --- Preview ---------------------------------------------------------------

def test_preview_is_a_sanitized_draft_banner_with_no_byline_or_date(client_as):
    a = client_as("admin")
    pid = page_id_of(save_page(a, title="Secret"))
    r = a.post("/admin/pages/preview", data={
        "title": "Secret", "body": "hi <script>alert(1)</script> **bold**",
        "page_id": str(pid), "csrf_token": csrf(a)})
    assert r.status_code == 200
    assert "Draft preview, not public" in r.text
    assert "<script" not in r.text and "<strong>bold</strong>" in r.text
    assert "None" not in r.text


def test_preview_follows_the_same_access_rules(client_as, other_editor):
    pid = page_id_of(save_page(client_as("admin"), assigned_editor_id=str(EDITOR_ID)))
    data = {"title": "t", "body": "b", "page_id": str(pid)}
    e = client_as("editor")
    assert e.post("/admin/pages/preview", data={**data, "csrf_token": csrf(e)}).status_code == 200
    assert other_editor.post("/admin/pages/preview",
                             data={**data, "csrf_token": csrf(other_editor)}).status_code == 403
    # an Editor cannot preview a brand new Page: they cannot create one
    r = e.post("/admin/pages/preview", data={"title": "t", "body": "b",
                                             "csrf_token": csrf(e)})
    assert r.status_code == 403


# --- Deactivation ----------------------------------------------------------

def test_deactivating_assigned_editor_unassigns_pages_and_user_list_counts_them(
        client_as, db_path):
    a, e = client_as("admin"), client_as("editor")
    pid = page_id_of(save_page(a, title="Service", assigned_editor_id=str(EDITOR_ID)))
    page_id_of(save_page(a, title="History", assigned_editor_id=str(EDITOR_ID)))
    assert "need a new" not in a.get("/admin/users").text
    a.post(f"/admin/users/{EDITOR_ID}/deactivate", data={"csrf_token": csrf(a)})
    assert row(db_path, pid, "assigned_editor_id") is None
    html = a.get("/admin/users").text
    assert "2 Pages need a new Assigned editor" in html
    assert a.get(f"/admin/pages/{pid}").status_code == 200


# --- CSRF and anonymous ----------------------------------------------------

def test_every_page_post_needs_a_csrf_token(client_as):
    a = client_as("admin")
    pid = page_id_of(save_page(a))
    for path in ("/admin/pages", f"/admin/pages/{pid}", f"/admin/pages/{pid}/delete",
                 f"/admin/pages/{pid}/unlock-slug", "/admin/pages/preview"):
        r = a.post(path, data={"title": "x", "body": "x"}, follow_redirects=False)
        assert r.status_code == 403, path


@pytest.mark.parametrize("path", ["/admin/pages", "/admin/pages/new", "/admin/pages/1"])
def test_anonymous_is_redirected_to_login(client, path):
    r = client.get(path, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


# --- Preview shows the real Navigation --------------------------------------

def nav_labels(html):
    nav = re.search(r"<nav>.*?</nav>", html, re.S)
    assert nav, "preview has no navigation"
    return re.findall(r"<span>([^<]+)</span>", nav.group(0))


def test_page_and_post_preview_show_the_published_navigation_in_order(client_as):
    a = client_as("admin")
    save_page(a, title="Welcome")  # Home
    save_page(a, title="Second", show_in_nav="on", nav_order="2", action="publish")
    save_page(a, title="First", show_in_nav="on", nav_order="1", action="publish")
    save_page(a, title="Draft Nav", show_in_nav="on", nav_order="0")
    save_page(a, title="Unlisted", action="publish")
    expected = ["Home", "First", "Second", "News"]
    page_preview = a.post("/admin/pages/preview", data={
        "title": "t", "body": "b", "csrf_token": csrf(a)}).text
    assert nav_labels(page_preview) == expected
    post_preview = a.post("/admin/posts/preview", data={
        "title": "t", "body": "b", "csrf_token": csrf(a)}).text
    assert nav_labels(post_preview) == expected
    assert "Draft preview, not public" in post_preview
    assert 'href="pages/' not in page_preview  # preview links must not point at the site
