from html import unescape

import bleach
import markdown as md


def strip_markdown(text: str) -> str:
    if not text:
        return ""
    rendered = md.markdown(text, extensions=["fenced_code", "tables"])
    stripped = bleach.clean(rendered, tags=[], attributes={}, strip=True)
    return unescape(stripped)


def normalize_user_text(text: str) -> str:
    cleaned = strip_markdown(text or "").strip()
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]
