"""Synchronization between crisalid structures and PeopleGroups"""

import logging
from collections.abc import Iterable

from django.db import transaction

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.organizations.models import Organization
from services.crisalid.models import CrisalidConfig, ResearcherStructure, Structure

logger = logging.getLogger(__name__)


def structures_root(organization: Organization) -> PeopleGroup:
    """parent group of all structures groups"""
    config = (
        CrisalidConfig.objects.filter(organization=organization)
        .select_related("structures_groups_root")
        .first()
    )
    if config and config.structures_groups_root:
        return config.structures_groups_root
    return PeopleGroup.update_or_create_root(organization)


def ensure_people_group(structure: Structure) -> PeopleGroup:
    """create the structure group if missing (initialized from the structure)"""
    people_group = structure.people_group
    if people_group is None:
        with transaction.atomic():
            people_group = PeopleGroup.objects.create(
                name=structure.name,
                description=structure.description,
                organization=structure.organization,
                parent=structures_root(structure.organization),
            )
            people_group.setup_permissions()
            structure.people_group = people_group
            structure.save(update_fields=["people_group"])
    return people_group


def sync_group_members(structure: Structure):
    """members of the structure group are users of researchers with an active relation
    to the structure or one of its sub-structures
    """
    people_group = structure.people_group
    if people_group is None:
        return

    # Also add child structures members to the current structure
    structures = [structure, *structure.descendants()]
    expected = set(
        ProjectUser.objects.filter(
            ResearcherStructure.active_query("researcher__researcherstructure__"),
            researcher__researcherstructure__structure__in=structures,
        ).values_list("pk", flat=True)
    )
    members_group = people_group.get_members()
    current = set(members_group.users.values_list("pk", flat=True))

    to_add = expected - current
    to_remove = current - expected
    if not to_add and not to_remove:
        return

    with transaction.atomic():
        members_group.users.add(*to_add)
        members_group.users.remove(*to_remove)
        people_group.set_role_groups_members()
        # trigger reindexing
        people_group.save()


def with_ancestors(structures: Iterable[Structure]) -> list[Structure]:
    """structures and their ancestors (members of a structure are in its ancestors groups)"""
    result = {}
    for structure in structures:
        for element in (structure, *structure.ancestors()):
            result.setdefault(element.pk, element)
    return list(result.values())


def sync_structures(structures: Iterable[Structure]):
    """sync groups (creation and members) of structures"""
    structures = list(structures)
    for structure in structures:
        ensure_people_group(structure)
    for structure in structures:
        sync_group_members(structure)
