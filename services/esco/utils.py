import traceback

from django.conf import settings

from .interface import EscoService
from .models import EscoOccupation, EscoSkill, EscoUpdateError


def create_missing_skills(cls) -> list[EscoSkill]:
    skills_data = EscoService.get_all_objects("skill")
    created_skills = []
    for skill_data in skills_data:
        skill, created = EscoSkill.objects.get_or_create(uri=skill_data["uri"])
        if created:
            created_skills.append(skill)
    return created_skills


def create_missing_occupations(cls) -> list[EscoOccupation]:
    occupations_data = EscoService.get_all_objects("occupation")
    created_occupations = []
    for occupation_data in occupations_data:
        occupation, created = EscoOccupation.objects.get_or_create(
            uri=occupation_data["uri"]
        )
        if created:
            created_occupations.append(occupation)
    return created_occupations


def update_skill_data(esco_skill: EscoSkill) -> EscoSkill:
    data = EscoService.get_object_from_uri("skill", esco_skill.uri)
    for language in settings.REQUIRED_LANGUAGES:
        title = data.get("preferredLabel", {}).get(language, "")
        description = data.get("description", {}).get(language, {}).get("literal", "")
        setattr(esco_skill, f"title_{language}", title)
        setattr(esco_skill, f"description_{language}", description)
    esco_skill.save()
    parents = data.get("_links", {}).get("broaderSkills", [])
    essential_for_skills = data.get("_links", {}).get("isEssentialForSkill", [])
    optional_for_skills = data.get("_links", {}).get("isOptionalForSkill", [])
    parents_uris = list(
        filter(lambda x: x != "", [parent.get("uri", "") for parent in parents])
    )
    essential_for_skills_uris = list(
        filter(
            lambda x: x != "", [skill.get("uri", "") for skill in essential_for_skills]
        )
    )
    optional_for_skills_uris = list(
        filter(
            lambda x: x != "", [skill.get("uri", "") for skill in optional_for_skills]
        )
    )
    esco_skill.parents.set(EscoSkill.objects.filter(uri__in=parents_uris))
    esco_skill.essential_for_skills.set(
        EscoSkill.objects.filter(uri__in=essential_for_skills_uris)
    )
    esco_skill.optional_for_skills.set(
        EscoSkill.objects.filter(uri__in=optional_for_skills_uris)
    )
    return esco_skill


def update_occupation_data(esco_occupation: EscoOccupation) -> EscoOccupation:
    data = EscoService.get_object_from_uri("occupation", esco_occupation.uri)
    for language in settings.REQUIRED_LANGUAGES:
        titles = data.get("alternativeTerms", {}).get(language, [])
        title = list(filter(lambda x: "male" in x["roles"], titles))
        if title:
            title = title[0]["label"]
        else:
            title = data.get("preferredLabel", {}).get(language, "")
        description = data.get("description", {}).get(language, {}).get("literal", "")
        setattr(esco_occupation, f"title_{language}", title)
        setattr(esco_occupation, f"description_{language}", description)
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
    esco_occupation.parents.set(EscoOccupation.objects.filter(uri__in=parents_uris))
    esco_occupation.essential_skills.set(
        EscoSkill.objects.filter(uri__in=essential_skills_uris)
    )
    esco_occupation.optional_skills.set(
        EscoSkill.objects.filter(uri__in=optional_skills_uris)
    )
    return esco_occupation


def update_esco_data(force_update: bool = False):
    new_skills = create_missing_skills()
    new_occupations = create_missing_occupations()
    skills = EscoSkill.objects.all() if force_update else new_skills
    occupations = EscoOccupation.objects.all() if force_update else new_occupations
    for skill in skills:
        try:
            update_skill_data(skill)
        except Exception as e:  # noqa: PIE786
            EscoUpdateError.objects.create(
                item_type=EscoSkill.__name__,
                item_id=skill.id,
                error=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )
    for occupation in occupations:
        try:
            update_occupation_data(occupation)
        except Exception as e:  # noqa: PIE786
            EscoUpdateError.objects.create(
                item_type=EscoOccupation.__name__,
                item_id=occupation.id,
                error=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )
