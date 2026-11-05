import os
from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/theme", tags=["Theme & Customization"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "templates"))

DEFAULT_LOGO_URL = "https://cdif4eosc.eu/wp-content/uploads/2026/10/logo-2x.png"
DEFAULT_FOOTER_TEXT = (
    "The project “CDIF4EOSC: Developing and implementing the Cross-Domain "
    "Interoperability Framework for EOSC” is funded by the European Union under Grant Agreement 101292473."
)


def _load_template_file(filename: str) -> Optional[str]:
    """Loads a custom HTML/text snippet from the templates directory if present and not just comments."""
    if not os.path.isdir(TEMPLATES_DIR):
        return None
    filepath = os.path.join(TEMPLATES_DIR, filename)
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return None
                # If file only contains HTML comments <!-- ... -->, treat as unset
                stripped = content
                while stripped.startswith("<!--") and "-->" in stripped:
                    end_idx = stripped.index("-->") + 3
                    stripped = stripped[end_idx:].strip()
                return content if stripped else None
        except Exception as e:
            print(f"Warning: could not read template {filepath}: {e}")
    return None


@router.get("/config")
async def get_theme_config():
    """
    Returns theme configuration for header and footer.
    Values can be overridden by templates/ (custom HTML/text) or environment variables (e.g. LOGO_URL).
    """
    raw_logo = os.getenv("LOGO_URL")
    logo_url = raw_logo.strip() if raw_logo and raw_logo.strip() else DEFAULT_LOGO_URL
    header_html = _load_template_file("header.html")
    footer_html = _load_template_file("footer.html")
    footer_text = _load_template_file("footer.txt") or DEFAULT_FOOTER_TEXT

    return {
        "logo_url": logo_url,
        "footer_text": footer_text,
        "header_html": header_html,
        "footer_html": footer_html,
        "templates_dir": TEMPLATES_DIR,
    }

