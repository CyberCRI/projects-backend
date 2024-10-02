import logging
from typing import List

from django.conf import settings

from services.esco.interface import EscoService
from services.wikipedia.interface import WikipediaService

from .models import Tag, TagClassification

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
    classification = TagClassification.get_or_create_esco_classification()
    classification.tags.add(*created_tags)
    return created_tags


def _update_skill_data(esco_skill: Tag) -> Tag:
    data = EscoService.get_object_from_uri(
        esco_skill.secondary_type, esco_skill.external_id
    )
    for language in settings.REQUIRED_LANGUAGES:
        title = data.get("preferredLabel", {}).get(language, "")
        description = data.get("description", {}).get(language, {}).get("literal", "")
        setattr(esco_skill, f"title_{language}", title)
        setattr(esco_skill, f"description_{language}", description)
    esco_skill.save()
    return esco_skill


def _update_occupation_data(esco_occupation: Tag) -> Tag:
    data = EscoService.get_object_from_uri(
        esco_occupation.secondary_type, esco_occupation.external_id
    )
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


def update_or_create_wikipedia_tags(wikipedia_qids: List[str]) -> List[Tag]:
    data = WikipediaService.get_by_ids(wikipedia_qids)
    tags = Tag.objects.bulk_create(
        [Tag(type=Tag.TagType.WIKIPEDIA, **item) for item in data],
        update_conflicts=True,
        unique_fields=["external_id"],
        update_fields=[
            "title",
            "description",
            *[
                f"{field}_{language}"
                for field in ["title", "description"]
                for language in settings.REQUIRED_LANGUAGES
            ],
        ],
    )
    classification = TagClassification.get_or_create_wikipedia_classification()
    classification.tags.add(*tags)
    return tags


def update_wikipedia_data():
    wikipedia_qids = Tag.objects.filter(type=Tag.TagType.WIKIPEDIA).values_list(
        "external_id", flat=True
    )
    update_or_create_wikipedia_tags(wikipedia_qids)
