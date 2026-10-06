"""T03: `cms publish`, tested at render_site() and the CLI."""
import re

import pytest

from app import posts, users
from app.cli import main
from app.publish import DraftInOutput, render_site


@pytest.fixture
def author(db_path):
    posts.init_posts(db_path)
    return users.get_user(db_path, 2)  # the seeded editor


def add(db_path, author, title, body="Body text.", slug="", publish=True):
    return posts.create_post(db_path, author=author, title=title, slug=slug,
                             body=body, publish=publish)


def site_text(out):
    return {p: p.read_text() for p in out.rglob("*") if p.is_file()}


def test_home_news_and_post_pages(db_path, author, tmp_path):
    add(db_path, author, "Rush Night", body="First para.\n\nSecond para.")
    out = render_site(tmp_path / "site", database=db_path)
    home = (out / "index.html").read_text()
    assert "Rush Night" in home and "First para." in home
    assert "Second para." not in home
    assert "Rush Night" in (out / "news.html").read_text()
    page = (out / "posts" / "rush-night.html").read_text()
    assert "Demo Editor" in page and "Second para." in page


def test_home_shows_only_5_latest_news_lists_all_newest_first(db_path, author, tmp_path):
    for i in range(7):
        pid = add(db_path, author, f"Story {i}")
        with posts.connect(db_path) as conn:
            conn.execute("update posts set published_at=? where id=?",
                         (f"2026-01-0{i + 1}T00:00:00+00:00", pid))
    out = render_site(tmp_path / "site", database=db_path)
    home = (out / "index.html").read_text()
    assert "Story 6" in home and "Story 2" in home
    assert "Story 1" not in home and "Story 0" not in home
    news = (out / "news.html").read_text()
    assert news.index("Story 6") < news.index("Story 3") < news.index("Story 0")


def test_drafts_are_absent(db_path, author, tmp_path):
    add(db_path, author, "Secret Draft Title", slug="secret-slug", publish=False)
    add(db_path, author, "Public One")
    out = render_site(tmp_path / "site", database=db_path)
    for text in site_text(out).values():
        assert "Secret Draft Title" not in text and "secret-slug" not in text
    assert not (out / "posts" / "secret-slug.html").exists()


def test_post_set_back_to_draft_is_absent_next_render(db_path, author, tmp_path):
    pid = add(db_path, author, "Take Me Down")
    out = render_site(tmp_path / "site", database=db_path)
    assert (out / "posts" / "take-me-down.html").exists()
    posts.update_post(db_path, pid, title="Take Me Down", body="x", slug=None,
                      action="draft")
    out = render_site(tmp_path / "site", database=db_path)
    assert not (out / "posts" / "take-me-down.html").exists()
    assert all("Take Me Down" not in t for t in site_text(out).values())


def test_all_paths_relative(db_path, author, tmp_path):
    add(db_path, author, "Rel")
    out = render_site(tmp_path / "site", database=db_path)
    for text in site_text(out).values():
        assert 'href="/' not in text and 'src="/' not in text
    page = (out / "posts" / "rel.html").read_text()
    assert 'href="../style.css"' in page and 'href="../index.html"' in page


def test_markdown_is_sanitized(db_path, author, tmp_path):
    add(db_path, author, "Evil",
        body='<script>alert(1)</script>\n\n<img src=x onerror=alert(2)>\n\nok')
    out = render_site(tmp_path / "site", database=db_path)
    for text in site_text(out).values():
        assert "<script" not in text and "onerror=" not in text


def test_no_email_or_login_in_output(db_path, author, tmp_path):
    add(db_path, author, "Who")
    out = render_site(tmp_path / "site", database=db_path)
    for text in site_text(out).values():
        assert "editor@example.test" not in text


def test_leaked_draft_aborts_and_leaves_no_half_site(db_path, author, tmp_path, monkeypatch):
    add(db_path, author, "Fine")
    add(db_path, author, "Leaky Draft", slug="leaky", publish=False)
    from app import publish
    real = publish.render_markdown
    monkeypatch.setattr(publish, "render_markdown",
                        lambda t: real(t) + "<h1>Leaky Draft</h1>")  # simulates a leak
    out = tmp_path / "site"
    with pytest.raises(DraftInOutput) as exc:
        render_site(out, database=db_path)
    assert "Draft" in str(exc.value)
    assert not out.exists()


def test_cli_summary_lists_items_and_refuses_on_leak(db_path, author, tmp_path,
                                                     monkeypatch, capsys):
    from app import settings
    add(db_path, author, "Listed Post")
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    assert main(["publish"]) == 0
    assert "Listed Post" in capsys.readouterr().out
    from app import publish
    monkeypatch.setattr(publish, "render_markdown", lambda t: "<h1>Draft-Leak</h1>")
    add(db_path, author, "Draft-Leak", slug="dl", publish=False)
    assert main(["publish"]) == 1
    assert "Draft" in capsys.readouterr().out


def test_draft_titled_like_nav_word_does_not_block_publish(db_path, author, tmp_path):
    add(db_path, author, "News", slug="news-draft", publish=False)
    add(db_path, author, "Real Story")
    out = render_site(tmp_path / "site", database=db_path)
    assert (out / "posts" / "real-story.html").exists()
