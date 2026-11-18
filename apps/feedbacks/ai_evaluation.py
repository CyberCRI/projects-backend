from __future__ import annotations

import html
import re
from typing import Any

import jsonschema
from django.template import (
    Context,
    Engine,
    Template,
    TemplateDoesNotExist,
    TemplateSyntaxError,
)

from apps.projects.models import Project, ProjectTab
from services.mistral.interface import MistralService

from .exceptions import (
    AIEvaluationInvalidPromptError,
    AIEvaluationLLMError,
    AIEvaluationSchemaMismatchError,
)

_TAG_RE = re.compile(r"<[^>]+>")
_LINK_RE = re.compile(r"""(?is)<a\b[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""")
_ENGINE = Engine(autoescape=False, string_if_invalid="")


def _inline_link(match: re.Match) -> str:
    """`<a href="url">label</a>` -> `label (url)`, so the URL survives flattening."""
    url = html.unescape(match.group(1)).strip()
    label = _TAG_RE.sub("", match.group(2)).strip()
    if not url.startswith(("http://", "https://")):
        return label
    if not label or html.unescape(label) == url:
        return url
    return f"{label} ({url})"


def html_to_text(raw: str | None) -> str:
    """Flatten rich text to plain text, keeping headings, lists and link URLs."""
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n")
    if "<" not in text:
        return text.strip()

    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    text = _LINK_RE.sub(_inline_link, text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|blockquote|section)>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "\n- ", text)
    text = re.sub(
        r"(?i)<h([1-6])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)) + " ", text
    )
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def localized(instance: Any, field: str, language: str | None) -> str:
    """Prefer the `<field>_<language>` translation, fall back to the base field.

    The value is returned as plain text (rich text is flattened).
    """
    keys = [f"{field}_{language}", field] if language else [field]
    for key in keys:
        value = getattr(instance, key, None)
        if isinstance(value, str) and value.strip():
            return html_to_text(value)
    return ""


def template_key(slug: str) -> str:
    """Template variables cannot contain `-`, so `my-tab` becomes `my_tab`."""
    return slug.replace("-", "_")


def _tab_context(tab: ProjectTab, language: str | None) -> dict[str, Any]:
    return {
        "title": localized(tab, "title", language),
        "type": tab.type,
        "description": localized(tab, "description", language),
        "items": [
            {
                "title": localized(item, "title", language),
                "content": localized(item, "content", language),
                "created_at": item.created_at.isoformat(),
            }
            for item in tab.items.all()
        ],
    }


def build_project_context(project: Project, language: str | None = "en") -> dict:
    """Walkable, prompt-friendly view of a project, as plain text.

    Tabs are keyed by slug with `-` replaced by `_` (template variables cannot
    contain `-`), so the tab `my-tab` is `{{ project.tabs.my_tab.description }}`.
    Loop over them in display order with `{% for tab in project.tabs.values %}`
    (a tab slugged `values`, `items` or `keys` would shadow the dict method).
    """
    return {
        "id": project.id,
        "slug": project.slug,
        "title": localized(project, "title", language),
        "purpose": localized(project, "purpose", language),
        "description": localized(project, "description", language),
        "language": project.language,
        "life_status": project.life_status,
        "sdgs": list(project.sdgs),
        "categories": [
            localized(category, "name", language)
            for category in project.categories.all()
        ],
        "tags": [localized(tag, "title", language) for tag in project.tags.all()],
        "tabs": {
            template_key(tab.slug): _tab_context(tab, language)
            for tab in project.additional_tabs.all()
        },
        "blog_entries": [
            {
                "title": localized(entry, "title", language),
                "content": localized(entry, "content", language),
                "created_at": entry.created_at.isoformat(),
            }
            for entry in project.blog_entries.all()
        ],
        "goals": [
            {
                "title": localized(goal, "title", language),
                "description": localized(goal, "description", language),
                "deadline_at": goal.deadline_at.isoformat() if goal.deadline_at else "",
                "status": goal.status,
            }
            for goal in project.goals.all()
        ],
        "locations": [location.title for location in project.locations.all()],
        "attached_links": [
            {
                "title": link.title,
                "url": link.site_url,
                "description": link.description,
                "category": link.category,
            }
            for link in project.links.all()
        ],
        "attached_files": [
            {"title": file.title, "description": file.description}
            for file in project.files.all()
        ],
        "members_count": project.get_all_members().count(),
    }


def render_prompt(template: str, context: dict[str, Any]) -> str:
    """Render one prompt. Unknown variables render as an empty string."""
    try:
        return (
            Template(template, engine=_ENGINE)
            .render(Context(context, autoescape=False))
            .strip()
        )
    except (TemplateSyntaxError, TemplateDoesNotExist) as exc:
        raise AIEvaluationInvalidPromptError(str(exc)) from exc


def evaluate(
    project: Project,
    system: list[str],
    prompts: list[str],
    json_schema: dict[str, Any],
    language: str | None = "en",
) -> dict[str, Any]:
    """Render the prompts for `project` and return an answer matching the schema."""
    context = {"project": build_project_context(project, language)}
    rendered_system = [render_prompt(message, context) for message in system]
    rendered_prompts = [render_prompt(message, context) for message in prompts]

    try:
        result = MistralService.get_structured_chat_response(
            rendered_system, rendered_prompts, json_schema
        )
    except Exception as exc:  # noqa: BLE001 - any provider/parsing failure
        raise AIEvaluationLLMError(f"{type(exc).__name__}: {exc}") from exc

    try:
        jsonschema.validate(result, json_schema)
    except jsonschema.ValidationError as exc:
        raise AIEvaluationSchemaMismatchError(exc.message) from exc
    return result
