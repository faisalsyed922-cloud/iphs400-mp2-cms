"""S1: every admin-only route refuses an Editor and sends an anonymous visitor to login.

The routes under test are not listed by hand. A route is admin-only when
`require_admin` appears anywhere in its dependency tree, so a new admin-only
route is covered the moment it is written.
"""
import tempfile
from pathlib import Path

import pytest
from conftest import DEMO_USERS, token_from
from fastapi.routing import APIRoute

from app import pages, users
from app.main import create_app
from app.security import require_admin


def depends_on(dependant, target) -> bool:
    return any(sub.call is target or depends_on(sub, target)
               for sub in dependant.dependencies)


def walk(routes, prefix="", inherited=()):
    """Yield (APIRoute, full path, dependencies inherited from include_router).

    FastAPI 0.1xx+ keeps included routers as wrappers around `original_router`
    instead of flattening them into `app.routes`, so descend into those.
    """
    for route in routes:
        if isinstance(route, APIRoute):
            yield route, prefix + route.path_format, inherited
        elif hasattr(route, "original_router"):
            context = route.include_context
            yield from walk(route.original_router.routes, prefix + context.prefix,
                            inherited + tuple(d.dependency for d in context.dependencies))


def admin_only_routes():
    app = create_app(database=Path(tempfile.mkdtemp()) / "collect.db")
    return sorted((method, path)
                  for route, path, inherited in walk(app.routes)
                  if require_admin in inherited or depends_on(route.dependant, require_admin)
                  for method in route.methods)


ADMIN_ONLY = admin_only_routes()


@pytest.fixture
def seeded_ids(db_path, client):
    """The ids a path parameter can take, one per kind of seeded item.

    Depends on `client` because building the app is what creates the tables.
    """
    page_id = pages.create_page(db_path, title="Seeded", slug="seeded", body="x",
                                assigned_editor_id=None, show_in_nav=False,
                                nav_order=0, is_home=False)
    admin = users.get_user_by_email(db_path, DEMO_USERS["admin"]["email"])
    return {"page_id": page_id, "user_id": admin["id"]}


def fill(path: str, ids: dict) -> str:
    for name, value in ids.items():
        path = path.replace("{%s}" % name, str(value))
    assert "{" not in path, f"no seeded id for a path parameter in {path}"
    return path


def test_the_marker_finds_admin_only_routes():
    found = {path for _, path in ADMIN_ONLY}
    assert "/admin/users" in found
    assert "/admin/pages/{page_id}/delete" in found
    assert "/admin/pages/{page_id}" not in found  # an Editor edits their own Page


@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_editor_cannot_use_admin_only_route(client_as, seeded_ids, method, path):
    editor = client_as("editor")
    # A valid CSRF token, so a 403 here means "not an Admin", not "bad token".
    data = {"csrf_token": token_from(editor.get("/admin").text)}
    response = editor.request(method, fill(path, seeded_ids), data=data,
                              follow_redirects=False)
    assert response.status_code in (302, 303, 403), f"{method} {path}"


@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_anonymous_is_sent_to_login(client, seeded_ids, method, path):
    response = client.request(method, fill(path, seeded_ids), follow_redirects=False)
    assert response.status_code in (302, 303), f"{method} {path}"
    assert response.headers["location"] == "/login"
