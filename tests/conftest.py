"""Shared test fixtures.

`client` gives you the app. `client_as(role)` gives you a client that is logged
in as a seeded user of that role — it works as soon as your login route exists,
so access-control tests stay one line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code in (302, 403)

Every app built here runs against its own temporary database, seeded with the
demo users below.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import users
from app.main import create_app

# Matches scripts/seed_demo.py. Passwords come from the environment there; in
# tests they are fixed and meaningless.
DEMO_USERS = {
    "admin": {"email": "admin@example.test", "password": "test-admin-pw",
              "display_name": "Demo Admin"},
    "editor": {"email": "editor@example.test", "password": "test-editor-pw",
               "display_name": "Demo Editor"},
}


def token_from(html: str) -> str:
    """Pull the CSRF token out of a rendered form."""
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "page has no CSRF token field"
    return match.group(1)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    users.init_db(path)
    for role, info in DEMO_USERS.items():
        users.create_user(path, email=info["email"], password=info["password"],
                          role=role, display_name=info["display_name"])
    return path


@pytest.fixture
def make_client(db_path):
    """Build a fresh, anonymous client against the temporary database."""

    def _make() -> TestClient:
        return TestClient(create_app(database=db_path))

    return _make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


@pytest.fixture
def client_as(make_client):
    """Return a factory: client_as("editor") -> a logged-in TestClient."""

    def _login(role: str) -> TestClient:
        user = DEMO_USERS[role]
        c = make_client()
        form = c.get("/login")
        if form.status_code == 404:
            pytest.skip("No /login route yet — build the login ticket first.")
        response = c.post("/login", data={"email": user["email"],
                                          "password": user["password"],
                                          "csrf_token": token_from(form.text)},
                          follow_redirects=False)
        # A failed login re-renders the form with a 200, so only a redirect
        # proves the session was started.
        assert response.status_code in (302, 303), (
            f"Login as {role} failed with {response.status_code}: expected a redirect")
        return c

    return _login
