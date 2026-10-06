"""T04: `cms deploy`, tested through the cms entry point with the push stubbed."""
import pytest

from app import deploy, posts, settings, users
from app.cli import main


@pytest.fixture
def env(db_path, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    posts.init_posts(db_path)
    posts.create_post(db_path, author=users.authenticate(db_path, "editor@example.test", "test-editor-pw"), title="Rush Night",
                      slug="", body="Come by.", publish=True)
    return db_path


class Push:
    """Stub for the real push: records calls, returns a chosen exit code."""

    def __init__(self, code=0):
        self.code, self.calls = code, []

    def __call__(self, site, message):
        self.calls.append(site)
        return self.code


def deploy_with(answer, push):
    return main(["deploy"], push=push, confirm=lambda prompt: answer)


def test_deploy_without_a_site_says_to_publish_first(env, capsys):
    push = Push()
    assert deploy_with("y", push) == 1
    assert "cms publish" in capsys.readouterr().out
    assert push.calls == []


def test_declining_pushes_nothing_exits_cleanly_and_records_nothing(env):
    main(["publish"])
    for answer in ("n", "", "no"):
        push = Push()
        assert deploy_with(answer, push) == 0
        assert push.calls == []
    assert deploy.last_deploy(env) is None


def test_confirming_pushes_only_the_static_site_and_records_the_time(env):
    main(["publish"])
    push = Push()
    assert deploy_with("y", push) == 0
    assert push.calls == [settings.SITE]
    assert deploy.last_deploy(env)


def test_a_failed_push_is_not_recorded(env):
    main(["publish"])
    assert deploy_with("y", Push(code=1)) == 1
    assert deploy.last_deploy(env) is None


def test_pushed_site_holds_only_generated_pages(env):
    """The database and .env sit beside site/, never inside the folder that is pushed."""
    (settings.SITE.parent / ".env").write_text("CMS_SECRET_KEY=x")
    main(["publish"])
    push = Push()
    deploy_with("y", push)
    assert push.calls == [settings.SITE]
    files = [p for p in push.calls[0].rglob("*") if p.is_file()]
    assert files and all(p.suffix in (".html", ".css") for p in files)


def test_root_absolute_paths_stop_the_deploy(env, capsys):
    main(["publish"])
    (settings.SITE / "index.html").write_text('<a href="/news.html">x</a>')
    push = Push()
    assert deploy_with("y", push) == 1
    assert push.calls == [] and "index.html" in capsys.readouterr().out
    assert deploy.last_deploy(env) is None


def test_publish_never_pushes(env):
    push = Push()
    assert main(["publish"], push=push) == 0
    assert push.calls == [] and deploy.last_deploy(env) is None


@pytest.mark.parametrize("answer", ["y", "Y", "yes", " YES "])
def test_yes_answers_all_confirm(env, answer):
    main(["publish"])
    push = Push()
    assert deploy_with(answer, push) == 0 and len(push.calls) == 1


def test_root_absolute_css_url_stops_the_deploy(env):
    main(["publish"])
    (settings.SITE / "style.css").write_text("body { background: url(/bg.png); }")
    push = Push()
    assert deploy_with("y", push) == 1 and push.calls == []
