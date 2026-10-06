"""T06: temporary passwords, forced change, minimum length, cms reset-password."""
import re
import sqlite3

import pytest
from conftest import DEMO_USERS, token_from

from app import cli, users

EDITOR = DEMO_USERS["editor"]


def csrf(c):
    return token_from(c.get("/admin").text)


def editor_id(db_path):
    return sqlite3.connect(db_path).execute(
        "select id from users where email=?", (EDITOR["email"],)).fetchone()[0]


def log_in(make_client, email, password):
    c = make_client()
    r = c.post("/login", data={"email": email, "password": password,
                               "csrf_token": token_from(c.get("/login").text)},
               follow_redirects=False)
    return c, r


def reset(admin, uid):
    return admin.post(f"/admin/users/{uid}/reset-password",
                      data={"csrf_token": csrf(admin)})


def temp_from(response):
    match = re.search(r'data-temp-password="([^"]+)"', response.text)
    assert match, "temporary password not shown"
    return match.group(1)


def test_admin_reset_shows_temp_password_once_and_old_one_stops_working(
        client_as, make_client, db_path):
    admin = client_as("admin")
    r = reset(admin, editor_id(db_path))
    assert r.status_code == 200
    temp = temp_from(r)
    assert len(temp) >= users.MIN_PASSWORD
    assert "no-store" in r.headers["cache-control"]
    # Gone on revisit.
    assert temp not in admin.get(f"/admin/users/{editor_id(db_path)}").text
    assert log_in(make_client, EDITOR["email"], EDITOR["password"])[0] \
        .get("/admin", follow_redirects=False).status_code in (302, 303)
    assert log_in(make_client, EDITOR["email"], temp)[1].status_code == 303


def test_temp_password_is_not_logged(client_as, db_path, caplog):
    caplog.set_level("DEBUG")
    temp = temp_from(reset(client_as("admin"), editor_id(db_path)))
    assert temp not in caplog.text


def test_temp_password_login_must_change_before_anything_else(
        client_as, make_client, db_path):
    temp = temp_from(reset(client_as("admin"), editor_id(db_path)))
    c, _ = log_in(make_client, EDITOR["email"], temp)
    for path in ("/admin", "/admin/posts"):
        r = c.get(path, follow_redirects=False)
        assert r.status_code in (302, 303)
        assert r.headers["location"].endswith("/user/password")
    form = c.get("/user/password")
    assert form.status_code == 200
    assert str(users.MIN_PASSWORD) in form.text

    new = "my-own-new-password"
    r = c.post("/user/password", data={
        "current_password": temp, "new_password": new, "confirm_password": new,
        "csrf_token": token_from(form.text)}, follow_redirects=False)
    assert r.status_code == 303
    assert c.get("/admin", follow_redirects=False).status_code == 200
    assert log_in(make_client, EDITOR["email"], new)[1].status_code == 303
    assert log_in(make_client, EDITOR["email"], temp)[0] \
        .get("/admin", follow_redirects=False).status_code in (302, 303)


def test_change_password_rejects_short_mismatch_and_wrong_current(
        client_as, make_client, db_path):
    temp = temp_from(reset(client_as("admin"), editor_id(db_path)))
    c, _ = log_in(make_client, EDITOR["email"], temp)
    token = token_from(c.get("/user/password").text)

    def attempt(**over):
        data = {"current_password": temp, "new_password": "long-enough-pw-1",
                "confirm_password": "long-enough-pw-1", "csrf_token": token, **over}
        return c.post("/user/password", data=data, follow_redirects=False)

    assert attempt(new_password="short", confirm_password="short").status_code == 400
    assert attempt(confirm_password="different-pw-123").status_code == 400
    assert attempt(current_password="wrong-current-pw").status_code == 400
    assert attempt(new_password=temp, confirm_password=temp).status_code == 400
    assert c.get("/admin", follow_redirects=False).status_code in (302, 303)


def test_voluntary_password_change_works_for_any_user(client_as, make_client):
    c = client_as("editor")
    form = c.get("/user/password")
    assert form.status_code == 200
    new = "brand-new-password-9"
    r = c.post("/user/password", data={
        "current_password": EDITOR["password"], "new_password": new,
        "confirm_password": new, "csrf_token": token_from(form.text)},
        follow_redirects=False)
    assert r.status_code == 303
    assert log_in(make_client, EDITOR["email"], new)[1].status_code == 303


def test_minimum_enforced_when_creating_a_user(client_as):
    admin = client_as("admin")
    r = admin.post("/admin/users", data={
        "email": "new@example.test", "display_name": "New", "role": "editor",
        "password": "elevenchars", "csrf_token": csrf(admin)},
        follow_redirects=False)
    assert r.status_code == 400
    assert "12" in r.text


def test_reset_form_page_shows_minimum_when_creating(client_as):
    assert "12" in client_as("admin").get("/admin/users/new").text


def test_editor_cannot_reset_anyones_password(client_as, make_client, db_path):
    e = client_as("editor")
    r = e.post("/admin/users/1/reset-password", data={"csrf_token": csrf(e)},
               follow_redirects=False)
    assert r.status_code == 403
    assert log_in(make_client, "admin@example.test",
                  DEMO_USERS["admin"]["password"])[1].status_code == 303


def test_anonymous_cannot_reset(client):
    r = client.post("/admin/users/1/reset-password", data={},
                    follow_redirects=False)
    assert r.status_code in (302, 303, 403)


def test_reset_unknown_user_is_404(client_as):
    admin = client_as("admin")
    assert admin.post("/admin/users/999/reset-password",
                      data={"csrf_token": csrf(admin)}).status_code == 404


@pytest.fixture
def cli_db(db_path, monkeypatch):
    monkeypatch.setattr(cli.settings, "DATABASE_PATH", db_path)
    return db_path


def answers(monkeypatch, *values):
    it = iter(values)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(it))


def test_cli_resets_admin_own_password(cli_db, make_client, monkeypatch):
    answers(monkeypatch, "a-fresh-admin-pw1", "a-fresh-admin-pw1")
    assert cli.main(["reset-password", "Admin@Example.test"]) == 0
    c, r = log_in(make_client, "admin@example.test", "a-fresh-admin-pw1")
    assert r.status_code == 303
    assert c.get("/admin", follow_redirects=False).status_code == 200
    assert log_in(make_client, "admin@example.test",
                  DEMO_USERS["admin"]["password"])[0] \
        .get("/admin", follow_redirects=False).status_code in (302, 303)


def test_cli_unknown_email_is_a_clear_error(cli_db, monkeypatch, capsys):
    answers(monkeypatch, "a-fresh-admin-pw1", "a-fresh-admin-pw1")
    assert cli.main(["reset-password", "nobody@example.test"]) == 1
    assert "nobody@example.test" in capsys.readouterr().out


def test_cli_rejects_short_and_mismatched(cli_db, make_client, monkeypatch, capsys):
    answers(monkeypatch, "short", "short")
    assert cli.main(["reset-password", "admin@example.test"]) == 1
    assert "12" in capsys.readouterr().out
    answers(monkeypatch, "a-fresh-admin-pw1", "different-admin-pw1")
    assert cli.main(["reset-password", "admin@example.test"]) == 1
    assert log_in(make_client, "admin@example.test",
                  DEMO_USERS["admin"]["password"])[1].status_code == 303


def test_admin_cannot_reset_own_password_through_the_console(client_as):
    admin = client_as("admin")
    r = admin.post("/admin/users/1/reset-password", data={"csrf_token": csrf(admin)})
    assert r.status_code == 400
    assert admin.get("/admin", follow_redirects=False).status_code == 200


def test_cli_shows_the_minimum_before_prompting(cli_db, monkeypatch, capsys):
    answers(monkeypatch, "a-fresh-admin-pw1", "a-fresh-admin-pw1")
    cli.main(["reset-password", "admin@example.test"])
    assert "12" in capsys.readouterr().out


def test_create_admin_command_enforces_the_minimum(cli_db, monkeypatch, capsys):
    answers(monkeypatch, "short", "short")
    assert cli.main(["create-admin", "new-admin@example.test"]) == 1
    assert users.get_user_by_email(cli_db, "new-admin@example.test") is None
