"""T01: login, logout and CSRF, tested through the HTTP app."""
import sqlite3

from conftest import DEMO_USERS, token_from


def log_in(client, email, password, **extra):
    token = token_from(client.get("/login").text)
    return client.post("/login", data={"email": email, "password": password,
                                       "csrf_token": token, **extra},
                       follow_redirects=False)


def test_seeded_users_log_in_and_reach_the_console(client_as):
    for role in ("admin", "editor"):
        response = client_as(role).get("/admin")
        assert response.status_code == 200
        assert "hello admin" in response.text.lower()


def test_wrong_password_and_unknown_email_get_the_same_refusal(client):
    wrong = log_in(client, DEMO_USERS["admin"]["email"], "not-the-password")
    unknown = log_in(client, "nobody@example.test", "not-the-password")
    assert wrong.status_code == unknown.status_code == 200
    assert "invalid email or password" in wrong.text.lower()
    assert "invalid email or password" in unknown.text.lower()


def test_failed_login_does_not_start_a_session(client):
    log_in(client, DEMO_USERS["admin"]["email"], "not-the-password")
    assert client.get("/admin", follow_redirects=False).status_code in (302, 303)


def test_anonymous_admin_request_redirects_to_login(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"].endswith("/login")
    assert "hello admin" not in response.text.lower()


def test_logout_ends_the_session(client_as):
    c = client_as("admin")
    token = token_from(c.get("/admin").text)
    out = c.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    assert out.status_code in (302, 303)
    assert c.get("/admin", follow_redirects=False).status_code in (302, 303)


def test_stored_password_is_an_argon2_hash(db_path):
    rows = sqlite3.connect(db_path).execute(
        "select password_hash from users").fetchall()
    assert rows
    for (value,) in rows:
        assert value.startswith("$argon2")
        assert "test-admin-pw" not in value and "test-editor-pw" not in value


def test_login_without_csrf_token_is_rejected(client):
    response = client.post("/login", data={
        "email": DEMO_USERS["admin"]["email"],
        "password": DEMO_USERS["admin"]["password"]}, follow_redirects=False)
    assert response.status_code == 403
    assert client.get("/admin", follow_redirects=False).status_code in (302, 303)


def test_logout_without_csrf_token_is_rejected(client_as):
    c = client_as("admin")
    assert c.post("/logout", follow_redirects=False).status_code == 403
    assert c.get("/admin").status_code == 200


def test_session_cookie_lasts_eight_hours(client):
    response = client.get("/login")
    cookie = response.headers["set-cookie"].lower()
    assert "max-age=28800" in cookie


def test_deactivated_user_cannot_use_the_console(db_path, make_client):
    c = make_client()
    log_in(c, DEMO_USERS["editor"]["email"], DEMO_USERS["editor"]["password"])
    assert c.get("/admin").status_code == 200
    with sqlite3.connect(db_path) as conn:
        conn.execute("update users set is_active = 0")
    assert c.get("/admin", follow_redirects=False).status_code in (302, 303)
    assert "invalid email or password" in log_in(
        make_client(), DEMO_USERS["editor"]["email"],
        DEMO_USERS["editor"]["password"]).text.lower()
