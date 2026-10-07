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

CSS = (settings.STATIC / "style.css").read_text()


def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


class DraftInOutput(Exception):
    """A Draft's title or Slug would appear in the generated site."""


def _rows_where(database: Path, table: str, where: str, order: str) -> list:
    if not database.exists():
        return []
    with connect(database) as conn:
        if not conn.execute("select 1 from sqlite_master where name=?",
                            (table,)).fetchone():
            return []
        return conn.execute(
            f"select * from {table} where {where} order by {order}").fetchall()


def _posts_where(database: Path, where: str) -> list:
    return _rows_where(database, "posts", where, "published_at desc, id desc")


def _pages_where(database: Path, where: str) -> list:
    return _rows_where(database, "pages", where, "nav_order, title, id")


def _published_pages(database: Path) -> list:
    return _pages_where(database, "status='published'")


def _draft_pages(database: Path) -> list:
    return _pages_where(database, "status!='published'")


def _published_posts(database: Path) -> list:
    return _posts_where(database, "status='published'")


def _draft_rows(database: Path) -> list:
    return _posts_where(database, "status!='published'")


def _first_paragraph(html: str) -> str:
    match = re.search(r"<p>.*?</p>", html, re.S)
    return match.group(0) if match else ""


def _check_no_drafts(site: Path, database: Path) -> None:
    """Refuse if any Draft made it into any page of the site.

    Every post entry carries a data-post-id marker (pages a data-page-id one) and
    links to posts/<slug>.html (pages/<slug>.html). Both are compared with the
    Drafts straight from the database (ids and Slugs are unique within a kind),
    on every file, so a Draft leaking onto Home, News or the Navigation is
    caught as surely as one on its own page. Titles are not matched: a Draft
    called "News" must not block every publish.
    """
    kinds = (("post", "posts", _draft_rows(database)),
             ("page", "pages", _draft_pages(database)))
    for f in sorted(site.rglob("*")):
        if not f.is_file():
            continue
        text = f.read_text()
        for marker, folder, drafts in kinds:
            marked = {int(i) for i in re.findall(rf'data-{marker}-id="(\d+)"', text)}
            for draft in drafts:
                if (draft["id"] in marked or f"{folder}/{draft['slug']}.html" in text
                        or f.name == f"{draft['slug']}.html"
                        and f.parent.name == folder):
                    raise DraftInOutput(
                        f"Refusing to publish: the Draft \"{draft['title']}\" would "
                        f"appear in {f.relative_to(site)}. Drafts must never leave "
                        "the database. The site was not written.")


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


def navigation(database: Path) -> list[tuple[str, str]]:
    """Navigation as (label, site-relative href): Home, then the Published Pages
    marked for it in order, then News. The Publish run and Preview share this."""
    return ([("Home", "index.html")]
            + [(p["title"], f"pages/{p['slug']}.html")
               for p in _published_pages(database)
               if p["show_in_nav"] and not p["is_home"]]
            + [("News", "news.html")])


def _render_into(work: Path, database: Path) -> list[str]:
    env = environment()
    published = _published_posts(database)
    entries = []
    for post in published:
        body = render_markdown(post["body"])
        entries.append({
            "id": post["id"], "title": post["title"], "slug": post["slug"], "body": body,
            "excerpt": _first_paragraph(body),
            "date": (post["published_at"] or "")[:10],
            "byline": format_byline(post["byline_name"], post["byline_title"],
                                    post["byline_term"]),
            "href": f"posts/{post['slug']}.html",
        })

    page_entries = []
    for page in _published_pages(database):
        page_entries.append({
            "id": page["id"], "title": page["title"], "body": render_markdown(page["body"]),
            "href": f"pages/{page['slug']}.html", "in_nav": bool(page["show_in_nav"]),
            "is_home": bool(page["is_home"])})
    home_page = next((p for p in page_entries if p["is_home"]), None)

    (work / "style.css").write_text(CSS)
    (work / "posts").mkdir()
    (work / "pages").mkdir()

    links = navigation(database)

    def write(path: str, template: str, prefix: str, **ctx) -> None:
        # prefix is "" for top-level pages and "../" for pages in posts/ and pages/
        (work / path).write_text(env.get_template(template).render(
            title=settings.SITE_TITLE, subtitle=settings.SITE_SUBTITLE,
            css_path=prefix + "style.css",
            home_path=prefix + "index.html", news_path=prefix + "news.html",
            nav_links=[(label, prefix + href) for label, href in links],
            **ctx))

    write("index.html", "public/home.html", "", items=entries[:5], home_page=home_page)
    write("news.html", "public/news.html", "", items=entries)
    for e in entries:
        write(e["href"], "public/post.html", "../", post=e)
    for p in page_entries:
        write(p["href"], "public/page.html", "../", page=p)
    _check_no_drafts(work, database)
    return (["Home (index.html)", "News (news.html)"]
            + [f"Page: {p['title']} ({p['href']})" for p in page_entries]
            + [f"Post: {e['title']} ({e['href']})" for e in entries])


def render_site(out: Path | None = None, database: Path | None = None) -> Path:
    return render(out, database)[0]
