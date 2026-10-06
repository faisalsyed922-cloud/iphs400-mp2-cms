"""T05: admin-only user management, Deactivation, the last-Admin guard."""
import sqlite3

import pytest
from conftest import DEMO_USERS, token_from

from app import posts, users

ADMIN_GETS = ["/admin/users", "/admin/users/new", "/admin/users/1"]
ADMIN_POSTS = ["/admin/users", "/admin/users/1", "/admin/users/1/deactivate",
               "/admin/users/contact"]


def csrf(c):
    return token_from(c.get("/admin").text)


def new_user(c, **over):
    data = {"email": "sec@example.test", "display_name": "Sam Secretary",
            "title": "Secretary", "term": "2026–27", "role": "editor",
            "password": "temporary-pw-1", "csrf_token": csrf(c), **over}
    return c.post("/admin/users", data=data, follow_redirects=False)


def log_in(make_client, email, password):
    c = make_client()
    r = c.post("/login", data={"email": email, "password": password,
                               "csrf_token": token_from(c.get("/login").text)},
               follow_redirects=False)
    return c, r


def user_id(db_path, email):
    return sqlite3.connect(db_path).execute(
        "select id from users where email=?", (email,)).fetchone()[0]


@pytest.mark.parametrize("path", ADMIN_GETS)
def test_editor_and_anonymous_are_refused_every_get(client, client_as, path):
    assert client_as("editor").get(path, follow_redirects=False).status_code == 403
    r = client.get(path, follow_redirects=False)
    assert r.status_code in (302, 303) and r.headers["location"].endswith("/login")


@pytest.mark.parametrize("path", ADMIN_POSTS)
def test_editor_and_anonymous_are_refused_every_post(client, client_as, path):
    e = client_as("editor")
    assert e.post(path, data={"csrf_token": csrf(e)},
                  follow_redirects=False).status_code == 403
    assert client.post(path, data={}, follow_redirects=False).status_code in (302, 303, 403)


def test_editor_blocked_page_names_the_admin_and_the_contact_line(client_as):
    a = client_as("admin")
    a.post("/admin/users/contact", data={"contact_line": "Text 555-0100",
                                         "csrf_token": csrf(a)})
    r = client_as("editor").get("/admin/users")
    assert r.status_code == 403
    assert "Demo Admin" in r.text and "Text 555-0100" in r.text


def test_users_link_hidden_from_editors_shown_to_admin(client_as):
    assert "/admin/users" not in client_as("editor").get("/admin").text
    assert "/admin/users" in client_as("admin").get("/admin").text


def test_admin_creates_user_with_hashed_password(client_as, make_client, db_path):
    r = new_user(client_as("admin"))
    assert r.status_code == 303
    stored = sqlite3.connect(db_path).execute(
        "select password_hash, role, title, term from users where email=?",
        ("sec@example.test",)).fetchone()
    assert stored[0].startswith("$argon2") and "temporary-pw-1" not in stored[0]
    assert stored[1:] == ("editor", "Secretary", "2026–27")
    _, login = log_in(make_client, "sec@example.test", "temporary-pw-1")
    assert login.status_code == 303


def test_duplicate_email_is_a_clear_error(client_as):
    a = client_as("admin")
    assert new_user(a, email=DEMO_USERS["editor"]["email"]).status_code == 400


def test_admin_changes_role_title_and_term(client_as, db_path):
    a = client_as("admin")
    uid = user_id(db_path, DEMO_USERS["editor"]["email"])
    r = a.post(f"/admin/users/{uid}", data={
        "display_name": "Demo Editor", "title": "Treasurer", "term": "2027–28",
        "role": "admin", "csrf_token": csrf(a)}, follow_redirects=False)
    assert r.status_code == 303
    u = users.get_user(db_path, uid)
    assert (u["title"], u["term"], u["role"]) == ("Treasurer", "2027–28", "admin")


def test_deactivated_user_cannot_log_in_and_open_session_is_refused(
        client_as, make_client, db_path):
    editor = client_as("editor")
    assert editor.get("/admin").status_code == 200
    a = client_as("admin")
    uid = user_id(db_path, DEMO_USERS["editor"]["email"])
    r = a.post(f"/admin/users/{uid}/deactivate", data={"csrf_token": csrf(a)},
               follow_redirects=False)
    assert r.status_code == 303
    assert editor.get("/admin", follow_redirects=False).status_code in (302, 303)
    _, login = log_in(make_client, DEMO_USERS["editor"]["email"],
                      DEMO_USERS["editor"]["password"])
    assert login.status_code == 200  # refused, no redirect into the console
    assert users.get_user(db_path, uid) is not None


def test_deactivation_keeps_posts_and_bylines(client_as, db_path):
    uid = user_id(db_path, DEMO_USERS["editor"]["email"])
    author = users.get_user(db_path, uid)
    posts.init_posts(db_path)
    pid = posts.create_post(db_path, author=author, title="News", slug="news",
                            body="x", publish=True)
    before = posts.byline(posts.get_post(db_path, pid))
    a = client_as("admin")
    a.post(f"/admin/users/{uid}/deactivate", data={"csrf_token": csrf(a)})
    after = posts.get_post(db_path, pid)
    assert after is not None and posts.byline(after) == before


def test_last_active_admin_cannot_be_deactivated_or_demoted(client_as, db_path):
    a = client_as("admin")
    aid = user_id(db_path, DEMO_USERS["admin"]["email"])
    assert a.post(f"/admin/users/{aid}/deactivate",
                  data={"csrf_token": csrf(a)}).status_code == 400
    r = a.post(f"/admin/users/{aid}", data={
        "display_name": "Demo Admin", "title": "", "term": "", "role": "editor",
        "csrf_token": csrf(a)})
    assert r.status_code == 400
    u = users.get_user(db_path, aid)
    assert u["role"] == "admin" and u["is_active"]


def test_promoting_a_successor_first_allows_deactivating_the_original(
        client_as, db_path):
    a = client_as("admin")
    aid = user_id(db_path, DEMO_USERS["admin"]["email"])
    eid = user_id(db_path, DEMO_USERS["editor"]["email"])
    a.post(f"/admin/users/{eid}", data={"display_name": "Demo Editor", "title": "",
                                        "term": "", "role": "admin",
                                        "csrf_token": csrf(a)})
    r = a.post(f"/admin/users/{aid}/deactivate", data={"csrf_token": csrf(a)},
               follow_redirects=False)
    assert r.status_code == 303
    assert not users.get_user(db_path, aid)["is_active"]


def test_user_management_forms_need_csrf(client_as):
    a = client_as("admin")
    assert a.post("/admin/users", data={"email": "x@example.test"}).status_code == 403


def test_contact_line_never_reaches_the_static_site(client_as, db_path, tmp_path):
    from app import publish
    a = client_as("admin")
    a.post("/admin/users/contact", data={"contact_line": "SECRET-CONTACT-LINE",
                                         "csrf_token": csrf(a)})
    out, _ = publish.render(tmp_path / "site", db_path)
    pages = list(out.rglob("*.html"))
    assert pages
    assert all("SECRET-CONTACT-LINE" not in f.read_text() for f in pages)


def test_short_initial_password_is_refused(client_as):
    assert new_user(client_as("admin"), password="short-pw-11").status_code == 400
