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


def leak_drafts(monkeypatch):
    """Make the renderer treat every post, Drafts included, as Published."""
    from app import publish
    monkeypatch.setattr(publish, "_published_posts",
                        lambda db: publish._posts_where(db, "1=1"))


def test_leaked_draft_aborts_and_leaves_no_half_site(db_path, author, tmp_path, monkeypatch):
    add(db_path, author, "Leaky Draft", slug="leaky", publish=False)
    leak_drafts(monkeypatch)
    out = tmp_path / "site"
    with pytest.raises(DraftInOutput) as exc:
        render_site(out, database=db_path)
    assert "Leaky Draft" in str(exc.value) and "Draft" in str(exc.value)
    assert not out.exists()


def test_guard_catches_a_draft_on_the_home_page_alone(db_path, author, tmp_path):
    """Home is where people look; the guard must cover it, not just post pages."""
    from app.publish import _check_no_drafts
    pid = add(db_path, author, "Hidden Plans", slug="hidden", publish=False)
    site = tmp_path / "site"
    (site / "posts").mkdir(parents=True)
    (site / "news.html").write_text("<p>clean</p>")
    for leak in (f'<article data-post-id="{pid}"><h2>x</h2></article>',
                 '<a href="posts/hidden.html">x</a>'):
        (site / "index.html").write_text(leak)
        with pytest.raises(DraftInOutput, match="index.html"):
            _check_no_drafts(site, db_path)
    (site / "index.html").write_text("<p>clean</p>")
    _check_no_drafts(site, db_path)  # no raise


def test_cli_summary_lists_items_and_refuses_on_leak(db_path, author, tmp_path,
                                                     monkeypatch, capsys):
    from app import settings
    add(db_path, author, "Listed Post")
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    assert main(["publish"]) == 0
    assert "Listed Post" in capsys.readouterr().out
    add(db_path, author, "Draft-Leak", slug="dl", publish=False)
    leak_drafts(monkeypatch)
    assert main(["publish"]) == 1
    assert "Draft" in capsys.readouterr().out


def test_draft_titled_like_nav_word_does_not_block_publish(db_path, author, tmp_path):
    add(db_path, author, "News", slug="news-draft", publish=False)
    add(db_path, author, "Real Story")
    out = render_site(tmp_path / "site", database=db_path)
    assert (out / "posts" / "real-story.html").exists()


def test_site_is_named_for_the_chapter_and_never_the_starter_names(db_path, author, tmp_path):
    add(db_path, author, "Rush Night")
    out = render_site(tmp_path / "site", database=db_path)
    for path, text in site_text(out).items():
        if path.suffix != ".html":
            continue
        assert "Delta Tau Delta at Kenyon College" in text, path
        assert "Chi Chapter" in text, path
    for path, text in site_text(out).items():
        for old in ("Knox County", "Historical Society", "IPHS 400", "Mini-Project"):
            assert old not in text, f"{old!r} found in {path.name}"


# --- T07: Pages and Navigation ---------------------------------------------

def add_page(db_path, title, body="Page body.", publish=True, nav=False, order=0,
             home=False, slug=""):
    from app import pages
    pages.init_pages(db_path)
    return pages.create_page(db_path, title=title, slug=slug, body=body,
                             assigned_editor_id=None, show_in_nav=nav,
                             nav_order=order, is_home=home, publish=publish)


def nav_links(html):
    nav = re.search(r"<nav.*?</nav>", html, re.S).group(0)
    return re.findall(r'<a href="([^"]+)">([^<]+)</a>', nav)


def test_published_page_is_rendered_without_author_or_date(db_path, author, tmp_path):
    add_page(db_path, "Our History", body="Founded long ago.")
    out = render_site(tmp_path / "site", database=db_path)
    html = (out / "pages" / "our-history.html").read_text()
    assert "Founded long ago." in html and "Our History" in html
    assert "Demo Editor" not in html and not re.search(r"\d{4}-\d{2}-\d{2}", html)


def test_navigation_is_home_then_pages_in_order_then_news_on_every_page(
        db_path, author, tmp_path):
    add_page(db_path, "Welcome", home=True)
    add_page(db_path, "Zeta", nav=True, order=1)
    add_page(db_path, "Alpha", nav=True, order=2)
    add_page(db_path, "Unlisted", nav=False)
    add(db_path, author, "A Post")
    out = render_site(tmp_path / "site", database=db_path)
    titles = ["Home", "Zeta", "Alpha", "News"]
    assert [t for _, t in nav_links((out / "index.html").read_text())] == titles
    assert [t for _, t in nav_links((out / "news.html").read_text())] == titles
    top = nav_links((out / "index.html").read_text())
    assert [h for h, _ in top] == ["index.html", "pages/zeta.html",
                                   "pages/alpha.html", "news.html"]
    deep = nav_links((out / "posts" / "a-post.html").read_text())
    assert [h for h, _ in deep] == ["../index.html", "../pages/zeta.html",
                                    "../pages/alpha.html", "../news.html"]
    sub = nav_links((out / "pages" / "zeta.html").read_text())
    assert sub[0][0] == "../index.html" and sub[-1][0] == "../news.html"


def test_unlisted_published_page_exists_but_is_not_linked(db_path, author, tmp_path):
    add_page(db_path, "Rush Info", nav=False)
    out = render_site(tmp_path / "site", database=db_path)
    assert (out / "pages" / "rush-info.html").exists()
    for f in out.rglob("*.html"):
        if f.name != "rush-info.html":
            assert "rush-info" not in f.read_text()


def test_draft_page_is_absent_everywhere(db_path, author, tmp_path):
    add_page(db_path, "Secret Page Title", slug="secret-page", publish=False, nav=True)
    add_page(db_path, "Public Page", nav=True)
    out = render_site(tmp_path / "site", database=db_path)
    assert not (out / "pages" / "secret-page.html").exists()
    for text in site_text(out).values():
        assert "Secret Page Title" not in text and "secret-page" not in text


def test_home_shows_home_page_then_5_latest_posts(db_path, author, tmp_path):
    add_page(db_path, "Welcome Friends", body="Hello visitors.", home=True)
    for i in range(6):
        pid = add(db_path, author, f"Story {i}")
        with posts.connect(db_path) as conn:
            conn.execute("update posts set published_at=? where id=?",
                         (f"2026-01-0{i + 1}T00:00:00+00:00", pid))
    home = (render_site(tmp_path / "site", database=db_path) / "index.html").read_text()
    assert "Hello visitors." in home
    assert home.index("Hello visitors.") < home.index("Story 5") < home.index("Story 1")
    assert "Story 0" not in home


def test_draft_home_page_is_not_shown_on_home(db_path, author, tmp_path):
    add_page(db_path, "Hidden Welcome", body="Not yet.", home=True, publish=False)
    add(db_path, author, "A Post")
    home = (render_site(tmp_path / "site", database=db_path) / "index.html").read_text()
    assert "Not yet." not in home and "Hidden Welcome" not in home and "A Post" in home


def test_page_output_is_relative_and_sanitized(db_path, author, tmp_path):
    add_page(db_path, "Evil", nav=True, body='<script>alert(1)</script>\n\n'
             '<img src=x onerror=alert(2)>\n\n[out](https://example.org) ok')
    out = render_site(tmp_path / "site", database=db_path)
    for text in site_text(out).values():
        assert "<script" not in text and "onerror=" not in text
        assert 'href="/' not in text and 'src="/' not in text
    assert 'href="../style.css"' in (out / "pages" / "evil.html").read_text()


def test_leaked_draft_page_aborts_publish(db_path, author, tmp_path, monkeypatch):
    from app import publish
    add_page(db_path, "Leaky Page", slug="leaky-page", publish=False, nav=True)
    monkeypatch.setattr(publish, "_published_pages",
                        lambda db: publish._pages_where(db, "1=1"))
    with pytest.raises(DraftInOutput, match="Leaky Page"):
        render_site(tmp_path / "site", database=db_path)
    assert not (tmp_path / "site").exists()


def test_cli_summary_lists_pages(db_path, author, tmp_path, monkeypatch, capsys):
    from app import settings
    add_page(db_path, "Listed Page")
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    assert main(["publish"]) == 0
    assert "Listed Page" in capsys.readouterr().out


def test_seed_script_adds_a_draft_and_a_published_page(tmp_path, monkeypatch):
    import importlib.util
    import sqlite3
    from app import settings
    db = tmp_path / "seed.db"
    monkeypatch.setattr(settings, "DATABASE_PATH", db)
    monkeypatch.setenv("CMS_ADMIN_PASSWORD", "seed-admin-password")
    monkeypatch.setenv("CMS_EDITOR_PASSWORD", "seed-editor-password")
    spec = importlib.util.spec_from_file_location(
        "seed_demo", settings.ROOT / "scripts" / "seed_demo.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    assert seed.main() == 0 and seed.main() == 0  # re-runnable
    statuses = [r[0] for r in sqlite3.connect(db).execute("select status from pages")]
    assert "draft" in statuses and "published" in statuses
    assert sqlite3.connect(db).execute(
        "select count(*) from pages where is_home=1").fetchone()[0] == 1
