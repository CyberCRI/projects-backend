import traceback

from django.conf import settings

from .interface import EscoService
from .models import EscoTag, EscoUpdateError


def create_missing_tags() -> list[EscoTag]:
    skills_data = EscoService.get_all_objects(EscoTag.EscoTagType.SKILL)
    occupations_data = EscoService.get_all_objects(EscoTag.EscoTagType.OCCUPATION)
    created_tags = []
    for tag_data in skills_data + occupations_data:
        tag, created = EscoTag.objects.get_or_create(
            uri=tag_data["uri"],
            type=tag_data["type"],
        )
        if created:
            created_tags.append(tag)
    return created_tags


def _update_skill_data(esco_skill: EscoTag) -> EscoTag:
    data = EscoService.get_object_from_uri(esco_skill.type, esco_skill.uri)
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
    parents = data.get("_links", {}).get("broaderSkill", [])
    essential_for = data.get("_links", {}).get("isEssentialForSkill", [])
    optional_for = data.get("_links", {}).get("isOptionalForSkill", [])
    parents_uris = list(
        filter(lambda x: x != "", [parent.get("uri", "") for parent in parents])
    )
    essential_for_uris = list(
        filter(lambda x: x != "", [skill.get("uri", "") for skill in essential_for])
    )
    optional_for_uris = list(
        filter(lambda x: x != "", [skill.get("uri", "") for skill in optional_for])
    )
    esco_skill.parents.set(EscoTag.objects.filter(uri__in=parents_uris))
    esco_skill.essential_for.set(EscoTag.objects.filter(uri__in=essential_for_uris))
    esco_skill.optional_for.set(EscoTag.objects.filter(uri__in=optional_for_uris))
    return esco_skill


def _update_occupation_data(esco_occupation: EscoTag) -> EscoTag:
    data = EscoService.get_object_from_uri(esco_occupation.type, esco_occupation.uri)
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
    parents = data.get("_links", {}).get("broaderOccupation", [])
    essential_skills = data.get("_links", {}).get("hasEssentialSkill", [])
    optional_skills = data.get("_links", {}).get("hasOptionalSkill", [])
    parents_uris = list(
        filter(lambda x: x != "", [parent.get("uri", "") for parent in parents])
    )
    essential_skills_uris = list(
        filter(lambda x: x != "", [skill.get("uri", "") for skill in essential_skills])
    )
    optional_skills_uris = list(
        filter(lambda x: x != "", [skill.get("uri", "") for skill in optional_skills])
    )
    esco_occupation.parents.set(EscoTag.objects.filter(uri__in=parents_uris))
    esco_occupation.essential_skills.set(
        EscoTag.objects.filter(uri__in=essential_skills_uris)
    )
    esco_occupation.optional_skills.set(
        EscoTag.objects.filter(uri__in=optional_skills_uris)
    )
    return esco_occupation


def update_tag_data(esco_tag: EscoTag) -> EscoTag:
    try:
        if esco_tag.type == EscoTag.EscoTagType.SKILL:
            return _update_skill_data(esco_tag)
        if esco_tag.type == EscoTag.EscoTagType.OCCUPATION:
            return _update_occupation_data(esco_tag)
    except Exception as e:  # noqa: PIE786
        EscoUpdateError.objects.create(
            item_type=esco_tag.type,
            item_id=esco_tag.id,
            error=e.__class__.__name__,
            traceback=traceback.format_exc(),
        )
    return esco_tag


def update_esco_data(force_update: bool = False):
    new_tags = create_missing_tags()
    tags = EscoTag.objects.all() if force_update else new_tags
    for tag in tags:
        update_tag_data(tag)
