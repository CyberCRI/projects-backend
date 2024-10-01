import logging

from django.conf import settings

from services.esco.interface import EscoService
from services.wikipedia.interface import WikipediaService

from .models import Tag

logger = logging.getLogger(__name__)


def create_missing_tags() -> list[Tag]:
    skills_data = EscoService.get_all_objects(Tag.SecondaryTagType.SKILL)
    occupations_data = EscoService.get_all_objects(Tag.SecondaryTagType.OCCUPATION)
    created_tags = []
    for tag_data in skills_data + occupations_data:
        tag, created = Tag.objects.get_or_create(
            external_id=tag_data["uri"],
            type=Tag.TagType.ESCO,
            secondary_type=tag_data["type"],
        )
        if created:
            created_tags.append(tag)
    return created_tags


def _update_skill_data(esco_skill: Tag) -> Tag:
    data = EscoService.get_object_from_uri(
        esco_skill.secondary_type, esco_skill.external_id
    )
    default_title = ""
    default_description = ""
    for language in settings.REQUIRED_LANGUAGES:
        title = data.get("preferredLabel", {}).get(language, "")
        description = data.get("description", {}).get(language, {}).get("literal", "")
        setattr(esco_skill, f"title_{language}", title)
        setattr(esco_skill, f"description_{language}", description)
        if default_title == "":
            default_title = title
            esco_skill.title = default_title
        if default_description == "":
            default_description = description
            esco_skill.description = default_description
    esco_skill.save()
    return esco_skill


def _update_occupation_data(esco_occupation: Tag) -> Tag:
    data = EscoService.get_object_from_uri(
        esco_occupation.secondary_type, esco_occupation.external_id
    )
    default_title = ""
    default_description = ""
    for language in settings.REQUIRED_LANGUAGES:
        titles = data.get("alternativeTerms", {}).get(language, [])
        title = list(filter(lambda x: "male" in x["roles"], titles))
        if title and language == "fr":
            title = title[0]["label"]
        else:
            title = data.get("preferredLabel", {}).get(language, "")
        description = data.get("description", {}).get(language, {}).get("literal", "")
        setattr(esco_occupation, f"title_{language}", title)
        setattr(esco_occupation, f"description_{language}", description)
        if default_title == "":
            default_title = title
            esco_occupation.title = default_title
        if default_description == "":
            default_description = description
            esco_occupation.description = default_description
    esco_occupation.save()
    return esco_occupation


def update_tag_data(esco_tag: Tag) -> Tag:
    try:
        if esco_tag.secondary_type == Tag.SecondaryTagType.SKILL:
            return _update_skill_data(esco_tag)
        if esco_tag.secondary_type == Tag.SecondaryTagType.OCCUPATION:
            return _update_occupation_data(esco_tag)
    except Exception as e:  # noqa: PIE786
        logger.error(f"Error updating ESCO tag {esco_tag.external_id}: {e}")
    return esco_tag


def update_esco_data(force_update: bool = False):
    new_tags = create_missing_tags()
    tags = Tag.objects.filter(type=Tag.TagType.ESCO) if force_update else new_tags
    for tag in tags:
        update_tag_data(tag)


def update_or_create_wikipedia_tag(wikipedia_qid: str) -> dict:
    """
    Update or create a WikipediaTag instance.
    """
    data = WikipediaService.get_by_id(wikipedia_qid)
    for language in ["en", *settings.REQUIRED_LANGUAGES]:
        if not data.get("title_en", None):
            data["title_en"] = data.get(f"title_{language}", "")
        if not data.get("description_en", None):
            data["description_en"] = data.get(f"description_{language}", "")
    wikipedia_qid = data.pop("wikipedia_qid")
    tag, _ = Tag.objects.update_or_create(
        type=Tag.TagType.WIKIPEDIA,
        external_id=wikipedia_qid,
        defaults=data,
    )
    return tag


def update_wikipedia_data():
    wikipedia_tags = Tag.objects.filter(type=Tag.TagType.WIKIPEDIA)
    for tag in wikipedia_tags:
        update_or_create_wikipedia_tag(tag.external_id)
