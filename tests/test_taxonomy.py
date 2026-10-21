"""F2: categories and tags on Posts, tested at the HTTP app and the Publish run."""
import re

from app import posts, users
from app.cli import main
from app.publish import render_site
from conftest import token_from


def save(c, post_id=None, **fields):
    path = f"/admin/posts/{post_id}" if post_id else "/admin/posts"
    token = token_from(c.get("/admin/posts/new").text)
    data = {"title": "Rush Night", "slug": "", "body": "Body.", "action": "save",
            "csrf_token": token, **fields}
    return c.post(path, data=data, follow_redirects=False)


def post_id_of(response):
    assert response.status_code == 303, response.text
    return int(re.search(r"/admin/posts/(\d+)", response.headers["location"]).group(1))


def add(db_path, title, category="", tags="", publish=True):
    posts.init_posts(db_path)
    return posts.create_post(db_path, author=users.get_user(db_path, 2), title=title,
                             slug="", body="Body.", publish=publish,
                             category=category, tags=tags)


def test_step1_category_and_tags_persist_after_save(client_as):
    c = client_as("editor")
    pid = post_id_of(save(c, category="Events", tags="rush, social"))
    page = c.get(f"/admin/posts/{pid}").text
    assert 'name="category" value="Events"' in page
    assert 'name="tags" value="rush, social"' in page
    save(c, post_id=pid, category="Service", tags="  Rush ,, rush, Fall  ")
    page = c.get(f"/admin/posts/{pid}").text
    assert 'name="category" value="Service"' in page
    assert 'name="tags" value="Rush, Fall"' in page  # trimmed, blanks and repeats gone


def test_step1_post_form_refuses_a_post_without_csrf(client_as):
    c = client_as("editor")
    pid = post_id_of(save(c, category="Events"))
    response = c.post(f"/admin/posts/{pid}", data={
        "title": "Hijack", "category": "Evil", "action": "save"},
        follow_redirects=False)
    assert response.status_code in (400, 403)
    assert 'name="category" value="Events"' in c.get(f"/admin/posts/{pid}").text


def test_step2_content_list_filters_by_category(db_path, client_as):
    add(db_path, "Rush Night", category="Events")
    add(db_path, "Food Drive", category="Service")
    add(db_path, "No Category")
    c = client_as("admin")
    everything = c.get("/admin/content").text
    assert "Rush Night" in everything and "Food Drive" in everything
    filtered = c.get("/admin/content?category=events").text  # case-insensitive
    assert "Rush Night" in filtered
    assert "Food Drive" not in filtered and "No Category" not in filtered
    assert '<option value="service"' in filtered  # the dropdown lists every category


def test_step2_filter_matches_the_public_page_slug(db_path, client_as):
    add(db_path, "Exclaimed", category="Rush!")
    add(db_path, "Plain", category="rush")  # same public page as "Rush!"
    add(db_path, "Other", category="Service")
    c = client_as("admin")
    filtered = c.get("/admin/content?category=rush").text
    assert "Exclaimed" in filtered and "Plain" in filtered and "Other" not in filtered
    assert filtered.count('<option value="rush"') == 1  # one entry per public page


def test_step3_publish_writes_category_and_tag_pages(db_path, tmp_path, monkeypatch, capsys):
    from app import settings
    add(db_path, "Rush Night", category="Chapter Events", tags="rush, Big Social")
    add(db_path, "Food Drive", category="Service", tags="rush")
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    assert main(["publish"]) == 0
    site = tmp_path / "site"
    category = (site / "category" / "chapter-events.html").read_text()
    assert "Rush Night" in category and "Food Drive" not in category
    rush = (site / "tag" / "rush.html").read_text()
    assert "Rush Night" in rush and "Food Drive" in rush
    assert rush.index("Food Drive") < rush.index("Rush Night")  # newest first
    assert "Rush Night" in (site / "tag" / "big-social.html").read_text()
    assert "category/chapter-events.html" in capsys.readouterr().out


def test_step4_post_links_to_its_labels_relatively(db_path, tmp_path):
    add(db_path, "Rush Night", category="Chapter Events", tags="rush, Big Social")
    out = render_site(tmp_path / "site", database=db_path)
    page = (out / "posts" / "rush-night.html").read_text()
    for target in ("category/chapter-events.html", "tag/rush.html", "tag/big-social.html"):
        assert f'href="../{target}"' in page
        assert (out / "posts" / f"../{target}").resolve().exists()
    for f in out.rglob("*.html"):
        assert not re.search(r'(?:href|src)="/', f.read_text()), f
    index = (out / "tag" / "rush.html").read_text()
    assert 'href="../posts/rush-night.html"' in index and 'href="../style.css"' in index


def test_step5_draft_with_same_labels_is_absent_from_index_pages(db_path, tmp_path):
    add(db_path, "Public Post", category="Events", tags="rush")
    add(db_path, "Secret Draft", category="Events", tags="rush", publish=False)
    add(db_path, "Lonely Draft", category="Drafts Only", tags="hidden-tag", publish=False)
    out = render_site(tmp_path / "site", database=db_path)
    for index in ("category/events.html", "tag/rush.html"):
        text = (out / index).read_text()
        assert "Public Post" in text
        assert "Secret Draft" not in text and "secret-draft" not in text
    assert not (out / "category" / "drafts-only.html").exists()
    assert not (out / "tag" / "hidden-tag.html").exists()
    assert "Drafts Only" not in "".join(f.read_text() for f in out.rglob("*.html"))


def test_step1_category_or_tag_without_letters_is_refused(db_path, client_as):
    c = client_as("editor")
    for fields in ({"category": "!!!"}, {"category": "日本"}, {"tags": "rush, ???"}):
        response = save(c, **fields)
        assert response.status_code == 400
        assert "at least one letter or digit" in response.text
    assert posts.list_posts(db_path) == []  # nothing was saved
    pid = post_id_of(save(c, category="Events", tags="rush"))
    assert save(c, post_id=pid, category="@@", tags="rush").status_code == 400
    page = c.get(f"/admin/posts/{pid}").text
    assert 'name="category" value="Events"' in page  # the old values stand


def test_step4_post_without_a_category_or_tags_has_no_label_links(db_path, tmp_path):
    add(db_path, "Old Post")
    add(db_path, "Tagged Only", tags="rush")
    out = render_site(tmp_path / "site", database=db_path)
    plain = (out / "posts" / "old-post.html").read_text()
    assert "Category:" not in plain and "Tags:" not in plain and "category/" not in plain
    tagged = (out / "posts" / "tagged-only.html").read_text()
    assert "Category:" not in tagged and 'href="../tag/rush.html"' in tagged
    assert not (out / "category").exists()
