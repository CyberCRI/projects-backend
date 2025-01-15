import logging
from typing import Dict, List

from django.conf import settings

from services.esco.interface import EscoService
from services.wikipedia.interface import WikipediaService

from .models import Tag, TagClassification

logger = logging.getLogger(__name__)


def create_missing_esco_tags() -> list[Tag]:
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
    classification = TagClassification.get_or_create_default_classification(
        classification_type=TagClassification.TagClassificationType.ESCO
    )
    classification.tags.add(*created_tags)
    return created_tags


def _update_esco_tag_data(esco_skill: Tag) -> Tag:
    data = EscoService.get_object_from_uri(
        esco_skill.secondary_type, esco_skill.external_id
    )
    for language in settings.REQUIRED_LANGUAGES:
        title = data.get("preferredLabel", {}).get(language, "")
        description = data.get("description", {}).get(language, {}).get("literal", "")
        alternative_titles = data.get("alternativeLabel", {}).get(language, [])
        alternative_titles = ", ".join(alternative_titles)
        setattr(esco_skill, f"title_{language}", title)
        setattr(esco_skill, f"description_{language}", description)
        setattr(esco_skill, f"alternative_titles_{language}", alternative_titles)
    esco_skill.save()
    return esco_skill


def update_esco_tag_data(esco_tag: Tag) -> Tag:
    try:
        _update_esco_tag_data(esco_tag)
    except Exception as e:  # noqa: PIE786
        logger.error(f"Error updating ESCO tag {esco_tag.external_id}: {e}")
    return esco_tag


def update_esco_data(force_update: bool = False):
    new_tags = create_missing_esco_tags()
    tags = Tag.objects.filter(type=Tag.TagType.ESCO) if force_update else new_tags
    for tag in tags:
        update_esco_tag_data(tag)


def set_default_language_title_and_description(
    tag_data: Dict[str, str], default_language: str = "en"
) -> Dict[str, str]:
    """
    Make sure that the default language title and description are set in
    the tag data used to update or create the tag.
    """
    fallback_title = tag_data.pop("fallback_title", None)
    fallback_description = tag_data.pop("fallback_description", None)
    for language in ["en", *settings.REQUIRED_LANGUAGES]:
        if not tag_data.get("title"):
            tag_data["title"] = tag_data.get(f"title_{language}")
        if not tag_data.get("description"):
            tag_data["description"] = tag_data.get(f"description_{language}")
    if not tag_data.get("title"):
        tag_data["title"] = fallback_title
    if not tag_data.get("description"):
        tag_data["description"] = fallback_description
    return tag_data


def update_or_create_wikipedia_tags(wikipedia_qids: List[str]) -> List[Tag]:
    data = WikipediaService.get_by_ids(wikipedia_qids)
    data = [set_default_language_title_and_description(tag) for tag in data]
    tags = []
    for tag in data:
        external_id = tag.pop("external_id")
        tag, _ = Tag.objects.update_or_create(
            external_id=external_id,
            type=Tag.TagType.WIKIPEDIA,
            defaults=tag,
        )
        tags.append(tag)
    classification = TagClassification.get_or_create_default_classification(
        classification_type=TagClassification.TagClassificationType.WIKIPEDIA
    )
    classification.tags.add(*tags)
    return tags


def update_wikipedia_data():
    wikipedia_qids = Tag.objects.filter(type=Tag.TagType.WIKIPEDIA).values_list(
        "external_id", flat=True
    )
    update_or_create_wikipedia_tags(wikipedia_qids)
