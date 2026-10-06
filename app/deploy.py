"""Deploy: push the rendered static site to the gh-pages branch."""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.users import connect

_ROOT_ABSOLUTE = re.compile(
    r'''(?:(?:href|src)\s*=\s*["']|url\(\s*["']?)/(?!/)''')


def push_site(site: Path, message: str) -> int:
    """Push only `site` to gh-pages and return the exit code."""
    return subprocess.run(
        [sys.executable, "-m", "ghp_import", "-n", "-p", "-m", message, str(site)],
    ).returncode


def root_absolute_files(site: Path) -> list[Path]:
    """HTML and CSS files under `site` with root-absolute paths (they break on Pages)."""
    return [f.relative_to(site) for f in sorted(site.rglob("*"))
            if f.suffix in (".html", ".css") and _ROOT_ABSOLUTE.search(f.read_text())]


def record_deploy(database: Path) -> None:
    with connect(database) as conn:
        conn.execute("create table if not exists deploys (deployed_at text not null)")
        conn.execute("insert into deploys values (?)",
                     (datetime.now(timezone.utc).isoformat(timespec="seconds"),))


def last_deploy(database: Path) -> str | None:
    """When the last successful Deploy happened, or None if there has been none."""
    if not database.exists():
        return None
    with connect(database) as conn:
        if not conn.execute("select 1 from sqlite_master where name='deploys'").fetchone():
            return None
        row = conn.execute("select max(deployed_at) from deploys").fetchone()
        return row[0]
