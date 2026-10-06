"""Markdown -> sanitized HTML. Preview and the Publish run both call this."""
from __future__ import annotations

import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": True})

_TAGS = {"p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em", "ul", "ol",
         "li", "blockquote", "a", "code", "pre", "hr"}
_ATTRIBUTES = {"a": {"href", "title"}}


def render_markdown(text: str) -> str:
    """Render Markdown, then strip everything outside the allowlist.

    Raw HTML is removed (scripts, event handlers, images). Links keep only
    http, https and mailto URLs and always get rel="noopener noreferrer".
    """
    return nh3.clean(
        _md.render(text or ""),
        tags=_TAGS,
        attributes=_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
    )
