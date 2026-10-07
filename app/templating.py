"""The shared Jinja environment."""
from fastapi.templating import Jinja2Templates

from app import settings

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

# The console serves the shared stylesheet from /static; publish overrides css_path with a relative one.
templates.env.globals["css_path"] = "/static/style.css"
