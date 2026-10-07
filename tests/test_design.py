"""T14: shared Chapter stylesheet, palette contrast, relative paths."""
import re

import pytest

from app import posts, settings, users
from app.cli import main
from app.deploy import root_absolute_files

CSS = (settings.STATIC / "style.css").read_text()


def _tokens():
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", CSS))


def _lum(hex_):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _ratio(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_palette_tokens_are_defined_once_in_root():
    t = _tokens()
    assert {"purple", "snow", "gold"} <= t.keys()
    assert CSS.count(":root {") == 1


def test_text_pairs_meet_wcag_aa():
    t = _tokens()
    pairs = [("ink", "snow"), ("muted", "snow"), ("purple", "snow"), ("snow", "purple"),
             ("gold-light", "purple"), ("purple-deep", "gold-light"),
             ("error", "error-bg"), ("ink", "parchment")]
    for fg, bg in pairs:
        assert _ratio(t[fg], t[bg]) >= 4.5, (fg, bg)


def test_gold_is_never_a_text_colour_on_light():
    # `color: var(--gold)` would be body text on snow; only gold-light on purple is allowed.
    assert not re.search(r"color:\s*var\(--gold\)", CSS)


def test_console_serves_the_shared_stylesheet(client_as):
    c = client_as("admin")
    page = c.get("/admin")
    assert 'href="/static/style.css"' in page.text
    assert c.get("/static/style.css").text == CSS


@pytest.fixture
def env(db_path, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    return db_path


def test_published_site_uses_the_same_stylesheet_with_relative_paths(env):
    posts.init_posts(env)
    posts.create_post(env, author=users.authenticate(env, "editor@example.test", "test-editor-pw"),
                      title="Rush Night", slug="", body="Come by.", publish=True)
    main(["publish"])
    assert 'href="../style.css"' in (settings.SITE / "posts" / "rush-night.html").read_text()
    assert (settings.SITE / "style.css").read_text() == CSS
    assert 'href="style.css"' in (settings.SITE / "index.html").read_text()
    assert root_absolute_files(settings.SITE) == []


def test_font_stack_falls_back_to_system_serif():
    assert re.search(r"--serif:[^;]*Georgia[^;]*serif;", CSS)
