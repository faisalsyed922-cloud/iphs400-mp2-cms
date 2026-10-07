"""Configuration, read from the environment (never hard-code secrets)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    """Copy KEY=value lines from .env into the environment (never overriding)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv(ROOT / ".env")
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "app" / "static"
SITE = ROOT / "site"

DEV_SECRET_KEY = "dev-only-not-for-production"
SECRET_KEY = os.environ.get("CMS_SECRET_KEY", DEV_SECRET_KEY)
DATABASE_PATH = Path(os.environ.get("CMS_DATABASE", ROOT / "cms.db"))
SITE_TITLE = os.environ.get("CMS_SITE_TITLE", "Delta Tau Delta at Kenyon College")
SITE_SUBTITLE = os.environ.get("CMS_SITE_SUBTITLE", "Chi Chapter")
# Set this to your Pages URL once you deploy, e.g.
# https://yourname.github.io/iphs400-mp2-cms/
BASE_PATH = os.environ.get("CMS_BASE_PATH", "")
