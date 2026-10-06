"""T02: Posts, tested through the HTTP app."""
import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import users
from app.main import create_app
from conftest import token_from


def save_post(c, title="Rush night", body="Hello **world**", slug="", action="save",
              post_id=None, page="/admin/posts/new", **extra):
    """Submit the post form; return the response (redirects not followed)."""
    path = f"/admin/posts/{post_id}" if post_id else "/admin/posts"
    token = token_from(c.get(page).text)
    return c.post(path, data={"title": title, "slug": slug, "body": body,
                              "action": action, "csrf_token": token, **extra},
                  follow_redirects=False)


def created_id(response):
    assert response.status_code == 303, response.text
    return int(re.search(r"/admin/posts/(\d+)", response.headers["location"]).group(1))


def post_form(c, post_id, path_suffix, **data):
    token = token_from(c.get("/admin/posts/new").text)
    return c.post(f"/admin/posts/{post_id}{path_suffix}",
                  data={"csrf_token": token, **data}, follow_redirects=False)


@pytest.fixture
def other_editor(db_path, make_client):
    users.create_user(db_path, email="other@example.test", password="other-editor-pw",
                      role="editor", display_name="Other Editor")
    c = make_client()
    token = token_from(c.get("/login").text)
    c.post("/login", data={"email": "other@example.test",
                           "password": "other-editor-pw", "csrf_token": token})
    return c


# --- create, slug, list ---------------------------------------------------

def test_editor_creates_a_draft_with_generated_slug(client_as):
    c = client_as("editor")
    post_id = created_id(save_post(c, title="Spring Rush: Kickoff!"))
    page = c.get(f"/admin/posts/{post_id}").text
    assert "spring-rush-kickoff" in page
    assert "Draft" in page
    assert "Demo Editor" in page  # author
    listing = c.get("/admin/posts").text
    assert "Spring Rush: Kickoff!" in listing


def test_duplicate_slug_is_refused_with_a_clear_error(client_as):
    c = client_as("editor")
    created_id(save_post(c, title="Same Title"))
    response = save_post(c, title="Same Title")
    assert response.status_code == 400
    assert "already used" in response.text.lower()
    assert "Same Title" in response.text  # the form keeps what was typed


def test_slug_is_editable_until_first_published(client_as):
    c = client_as("editor")
    post_id = created_id(save_post(c, title="Old name"))
    response = save_post(c, title="Old name", slug="better-slug", post_id=post_id)
    assert response.status_code == 303
    assert "better-slug" in c.get(f"/admin/posts/{post_id}").text


def test_posts_persist_across_a_restart(client_as, db_path):
    created_id(save_post(client_as("editor"), title="Survives restart"))
    restarted = TestClient(create_app(database=db_path))
    token = token_from(restarted.get("/login").text)
    restarted.post("/login", data={"email": "admin@example.test",
                                   "password": "test-admin-pw", "csrf_token": token})
    assert "Survives restart" in restarted.get("/admin/posts").text


def test_anonymous_is_redirected_from_posts(client):
    response = client.get("/admin/posts", follow_redirects=False)
    assert response.status_code in (302, 303)


def test_post_forms_require_a_csrf_token(client_as):
    c = client_as("editor")
    response = c.post("/admin/posts", data={"title": "x", "body": "y"})
    assert response.status_code == 403


# --- publish, byline, slug lock --------------------------------------------

def test_publishing_snapshots_the_byline_and_locks_the_slug(client_as, db_path):
    c = client_as("editor")
    with sqlite3.connect(db_path) as conn:
        conn.execute("update users set title='Secretary', term='2026–27' "
                     "where email='editor@example.test'")
    post_id = created_id(save_post(c, title="News", action="publish"))
    page = c.get(f"/admin/posts/{post_id}").text
    assert "Published" in page
    assert "Demo Editor, Secretary, 2026–27" in page

    with sqlite3.connect(db_path) as conn:
        conn.execute("update users set title='Alumni chair', term='2027–28' "
                     "where email='editor@example.test'")
    page = c.get(f"/admin/posts/{post_id}").text
    assert "Demo Editor, Secretary, 2026–27" in page  # unchanged

    response = save_post(c, title="News", slug="sneaky", post_id=post_id)
    assert response.status_code == 303
    page = c.get(f"/admin/posts/{post_id}").text
    assert "sneaky" not in page  # editor's slug change ignored once locked
    assert 'name="slug"' in page and "disabled" in page.split('name="slug"')[1][:80] \
        or "readonly" in page.split('name="slug"')[1][:80]


def test_admin_can_unlock_a_slug_after_first_publish(client_as):
    editor, admin = client_as("editor"), client_as("admin")
    post_id = created_id(save_post(editor, title="Locked", action="publish"))
    assert post_form(editor, post_id, "/unlock-slug").status_code == 403
    assert post_form(admin, post_id, "/unlock-slug").status_code == 303
    save_post(editor, title="Locked", slug="fixed-slug", post_id=post_id)
    assert "fixed-slug" in editor.get(f"/admin/posts/{post_id}").text


def test_editing_a_published_post_keeps_it_published(client_as):
    c = client_as("editor")
    post_id = created_id(save_post(c, title="Live-ish", action="publish"))
    save_post(c, title="Live-ish fixed", post_id=post_id)
    page = c.get(f"/admin/posts/{post_id}").text
    assert "Live-ish fixed" in page
    assert 'data-status="published"' in page


def test_editor_can_set_their_own_post_back_to_draft(client_as):
    c = client_as("editor")
    post_id = created_id(save_post(c, title="Oops", action="publish"))
    save_post(c, title="Oops", action="draft", post_id=post_id)
    assert 'data-status="draft"' in c.get(f"/admin/posts/{post_id}").text


# --- permissions -------------------------------------------------------------

def test_editor_cannot_view_edit_or_delete_another_editors_post(client_as, other_editor):
    post_id = created_id(save_post(client_as("editor"), title="Mine"))
    assert other_editor.get(f"/admin/posts/{post_id}").status_code == 403
    assert save_post(other_editor, title="Hijack", post_id=post_id).status_code == 403
    token = token_from(other_editor.get("/admin/posts/new").text)
    response = other_editor.post(f"/admin/posts/{post_id}/delete",
                                 data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 403
    assert "Mine" in client_as("admin").get(f"/admin/posts/{post_id}").text


def test_editor_sees_other_peoples_posts_in_the_list(client_as, other_editor):
    created_id(save_post(client_as("editor"), title="Someone elses post"))
    assert "Someone elses post" in other_editor.get("/admin/posts").text


def test_editor_deletes_own_draft_but_not_a_published_post(client_as):
    c = client_as("editor")
    draft = created_id(save_post(c, title="Abandoned"))
    live = created_id(save_post(c, title="Announced", action="publish"))
    assert post_form(c, live, "/delete").status_code == 403
    assert post_form(c, draft, "/delete").status_code == 303
    listing = c.get("/admin/posts").text
    assert "Abandoned" not in listing and "Announced" in listing


def test_admin_edits_and_deletes_any_post(client_as):
    editor, admin = client_as("editor"), client_as("admin")
    post_id = created_id(save_post(editor, title="Editor wrote", action="publish"))
    assert save_post(admin, title="Admin fixed", post_id=post_id).status_code == 303
    assert "Admin fixed" in admin.get(f"/admin/posts/{post_id}").text
    assert post_form(admin, post_id, "/delete").status_code == 303
    assert admin.get(f"/admin/posts/{post_id}").status_code == 404


# --- preview -----------------------------------------------------------------

def preview(c, body, title="T"):
    token = token_from(c.get("/admin/posts/new").text)
    return c.post("/admin/posts/preview",
                  data={"title": title, "body": body, "csrf_token": token})


def test_preview_is_labelled_not_public(client_as):
    html = preview(client_as("editor"), "hi").text
    assert "Draft preview, not public" in html


def test_preview_strips_scripts_and_event_handlers(client_as):
    body = ('Hi <script>alert(1)</script> <img src=x onerror="alert(2)"> '
            '<b onclick="x()">bold</b>')
    html = preview(client_as("editor"), body).text
    assert "<script" not in html and "alert(1)" not in html
    assert "onerror" not in html and "onclick" not in html


def test_preview_renders_formatting_and_marks_outside_links(client_as):
    body = "# Big\n\n**bold** and *it*\n\n- a\n- b\n\n[out](https://example.org/x)"
    html = preview(client_as("editor"), body).text
    assert "<h1>Big</h1>" in html and "<strong>bold</strong>" in html
    assert "<li>a</li>" in html
    assert re.search(r'<a href="https://example.org/x"[^>]*rel="[^"]*noopener', html)


def test_preview_blocks_javascript_links(client_as):
    html = preview(client_as("editor"), "[x](javascript:alert(1))").text
    assert "href=\"javascript" not in html.lower()


def test_preview_requires_login_and_csrf(client, client_as):
    assert client.post("/admin/posts/preview", data={"body": "x"},
                       follow_redirects=False).status_code in (302, 303, 403)
    assert client_as("editor").post("/admin/posts/preview",
                                    data={"body": "x"}).status_code == 403


def test_every_post_route_refuses_a_missing_csrf_token(client_as):
    admin = client_as("admin")
    post_id = created_id(save_post(client_as("editor"), title="Guarded"))
    for suffix in ("", "/delete", "/unlock-slug"):
        response = admin.post(f"/admin/posts/{post_id}{suffix}",
                              data={"title": "x"}, follow_redirects=False)
        assert response.status_code == 403, suffix
    assert "Guarded" in admin.get(f"/admin/posts/{post_id}").text


def test_preview_of_a_draft_shows_its_authors_byline_not_the_viewers(client_as):
    post_id = created_id(save_post(client_as("editor"), title="Draft"))
    admin = client_as("admin")
    token = token_from(admin.get("/admin/posts/new").text)
    html = admin.post("/admin/posts/preview",
                      data={"title": "Draft", "body": "x", "post_id": post_id,
                            "csrf_token": token}).text
    assert "Demo Editor" in html and "Demo Admin" not in html
    assert "None" not in html
