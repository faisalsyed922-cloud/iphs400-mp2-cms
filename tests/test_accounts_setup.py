"""T01: creating the first Admin and seeding demo users."""
import importlib.util
import sqlite3
from pathlib import Path

from app import cli, settings
from app.main import create_app
from fastapi.testclient import TestClient
from conftest import token_from

SEED = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"


def load_seed():
    spec = importlib.util.spec_from_file_location("seed_demo", SEED)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def can_log_in(database, email, password):
    c = TestClient(create_app(database=database))
    token = token_from(c.get("/login").text)
    r = c.post("/login", data={"email": email, "password": password,
                               "csrf_token": token}, follow_redirects=False)
    return r.status_code == 303


def test_create_admin_asks_for_a_hidden_password(tmp_path, monkeypatch):
    db = tmp_path / "cms.db"
    monkeypatch.setattr(settings, "DATABASE_PATH", db)
    prompts = []

    def fake_getpass(prompt=""):
        prompts.append(prompt)
        return "a-long-enough-password"

    monkeypatch.setattr(cli.getpass, "getpass", fake_getpass)
    assert cli.main(["create-admin", "president@example.test"]) == 0
    assert prompts, "password must be requested through getpass"
    assert can_log_in(db, "president@example.test", "a-long-enough-password")
    role = sqlite3.connect(db).execute(
        "select role from users where email = 'president@example.test'").fetchone()
    assert role == ("admin",)


def test_create_admin_refuses_mismatched_passwords(tmp_path, monkeypatch):
    db = tmp_path / "cms.db"
    monkeypatch.setattr(settings, "DATABASE_PATH", db)
    answers = iter(["first-password-here", "different-password"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(answers))
    assert cli.main(["create-admin", "president@example.test"]) == 1
    assert not can_log_in(db, "president@example.test", "first-password-here")


def test_seed_creates_admin_and_editor_from_environment(tmp_path, monkeypatch):
    db = tmp_path / "cms.db"
    monkeypatch.setattr(settings, "DATABASE_PATH", db)
    monkeypatch.setenv("CMS_ADMIN_PASSWORD", "seed-admin-secret")
    monkeypatch.setenv("CMS_EDITOR_PASSWORD", "seed-editor-secret")
    seed = load_seed()
    assert seed.main() == 0
    assert can_log_in(db, "admin@example.test", "seed-admin-secret")
    assert can_log_in(db, "editor@example.test", "seed-editor-secret")
    assert seed.main() == 0  # safe to run twice


def test_seed_needs_passwords_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", tmp_path / "cms.db")
    monkeypatch.delenv("CMS_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("CMS_EDITOR_PASSWORD", raising=False)
    assert load_seed().main() == 1


def test_serve_refuses_the_public_dev_secret_key(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", settings.DEV_SECRET_KEY)
    assert cli.main(["serve"]) == 1


def test_dotenv_values_load_without_overriding_the_environment(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('# comment\nCMS_T01_A="quoted value"\nCMS_T01_B=from-file\n')
    monkeypatch.setenv("CMS_T01_B", "from-shell")
    monkeypatch.delenv("CMS_T01_A", raising=False)
    settings._load_dotenv(env)
    import os
    assert os.environ["CMS_T01_A"] == "quoted value"
    assert os.environ["CMS_T01_B"] == "from-shell"
    monkeypatch.delenv("CMS_T01_A")
