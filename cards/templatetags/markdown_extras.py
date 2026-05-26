import bleach
import markdown as md
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = frozenset({
    "p", "br", "strong", "em", "code", "pre", "blockquote",
    "ul", "ol", "li", "a", "h1", "h2", "h3", "h4",
})
ALLOWED_ATTRS = {"a": ["href", "title"]}


@register.filter(name="markdown")
def markdown_filter(text: str) -> str:
    html = md.markdown(text or "", extensions=["fenced_code", "tables"])
    clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    return mark_safe(clean)
