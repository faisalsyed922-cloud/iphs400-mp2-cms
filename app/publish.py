"""Render the public site into site/ as plain HTML.

T00 publishes a placeholder home page. As you build content types, extend
render_site() to write one file per published item. Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft that reaches site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "posts/x.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from markupsafe import escape
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import settings
from app.markdown import render_markdown
from app.posts import format_byline
from app.users import connect

CSS = """/* Minimal starter styles — make them yours. */
:root { color-scheme: light dark; }
body { font: 16px/1.6 system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem; }
header a { font-weight: 700; text-decoration: none; }
main { margin-block: 2rem; }
"""


def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


class DraftInOutput(Exception):
    """A Draft's title or Slug would appear in the generated site."""


def _posts_where(database: Path, where: str) -> list:
    if not database.exists():
        return []
    with connect(database) as conn:
        if not conn.execute("select 1 from sqlite_master where name='posts'").fetchone():
            return []
        return conn.execute(
            f"select * from posts where {where} order by published_at desc, id desc"
        ).fetchall()


def _published_posts(database: Path) -> list:
    return _posts_where(database, "status='published'")


def _draft_rows(database: Path) -> list:
    return _posts_where(database, "status!='published'")


def _first_paragraph(html: str) -> str:
    match = re.search(r"<p>.*?</p>", html, re.S)
    return match.group(0) if match else ""


def _check_no_drafts(site: Path, database: Path, published: list) -> None:
    """Refuse if a Draft's page, link or heading made it into the site.

    Matches the Draft's Slug as a post file or link, and its title only as
    a post page's heading, so a Draft called "News" does not trip over
    ordinary words on other pages.
    """
    ok_slugs = {p["slug"] for p in published}
    texts = {f: f.read_text() for f in site.rglob("*") if f.is_file()}
    for draft in _draft_rows(database):
        title, slug = draft["title"], draft["slug"]
        for f, text in texts.items():
            leaked_slug = slug not in ok_slugs and (
                f"posts/{slug}.html" in text or f == site / "posts" / f"{slug}.html")
            leaked_title = (f.parent == site / "posts" and slug not in ok_slugs
                            and f"<h1>{escape(title)}</h1>" in text)
            if leaked_slug or leaked_title:
                raise DraftInOutput(
                    f"Refusing to publish: the Draft \"{title}\" would appear in "
                    f"{f.relative_to(site)}. Drafts must never leave the database. "
                    "The site was not written.")


def render(out: Path | None = None, database: Path | None = None) -> tuple[Path, list[str]]:
    """Render Published content into `out`; return it and a list of rendered items.

    Builds in a sibling folder and swaps it in only after the Draft check
    passes, so a refusal never leaves a half-finished site.
    """
    out = out or settings.SITE
    database = database or settings.DATABASE_PATH
    work = out.parent / (out.name + ".building")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        items = _render_into(work, database)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    if out.exists():
        shutil.rmtree(out)
    work.rename(out)
    return out, items


def _render_into(work: Path, database: Path) -> list[str]:
    env = environment()
    published = _published_posts(database)
    entries = []
    for post in published:
        body = render_markdown(post["body"])
        entries.append({
            "title": post["title"], "slug": post["slug"], "body": body,
            "excerpt": _first_paragraph(body),
            "date": (post["published_at"] or "")[:10],
            "byline": format_byline(post["byline_name"], post["byline_title"],
                                    post["byline_term"]),
            "href": f"posts/{post['slug']}.html",
        })

    (work / "style.css").write_text(CSS)
    (work / "posts").mkdir()
    nav = {"home_path": "index.html", "news_path": "news.html"}

    def write(path: str, template: str, prefix: str, **ctx) -> None:
        # prefix is "" for top-level pages and "../" for pages in posts/
        (work / path).write_text(env.get_template(template).render(
            title=settings.SITE_TITLE, css_path=prefix + "style.css",
            home_path=prefix + nav["home_path"], news_path=prefix + nav["news_path"],
            **ctx))

    write("index.html", "public/home.html", "", items=entries[:5])
    write("news.html", "public/news.html", "", items=entries)
    for e in entries:
        write(e["href"], "public/post.html", "../", post=e)
    _check_no_drafts(work, database, published)
    return ["Home (index.html)", "News (news.html)"] + [
        f"Post: {e['title']} ({e['href']})" for e in entries]


def render_site(out: Path | None = None, database: Path | None = None) -> Path:
    return render(out, database)[0]
