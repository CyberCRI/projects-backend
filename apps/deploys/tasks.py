from django.core.management import call_command
from guardian.shortcuts import assign_perm, remove_perm

from apps.accounts.models import PeopleGroup
from apps.accounts.utils import (
    get_default_group,
    get_default_group_permissions,
    get_superadmins_group,
    get_superadmins_group_permissions,
)
from apps.commons.models import GroupData
from apps.commons.utils import clear_memory
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.skills.models import TagClassification
from projects.celery import app


def migrate():
    call_command("migrate")


@app.task(name="apps.deploys.tasks.rebuild_index")
@clear_memory
def rebuild_index():
    """
    python manage.py opensearch index rebuild --force
    """
    call_command("update_or_rebuild_index")


@app.task(name="apps.deploys.tasks.default_tag_classifications")
def default_tag_classifications():
    for classification_type in TagClassification.TagClassificationType.values:
        if classification_type != TagClassification.TagClassificationType.CUSTOM:
            TagClassification.get_or_create_default_classification(
                classification_type=classification_type
            )


@app.task(name="apps.deploys.tasks.reassign_base_groups_permissions")
def reassign_base_groups_permissions():
    """
    Assign base groups permissions
    - Default group
    - Superadmins group
    """

    # Default group
    default_group = get_default_group()
    default_group_permissions = get_default_group_permissions()
    current_default_group_permissions = default_group.permissions.all()
    default_group_permissions_to_remove = current_default_group_permissions.difference(
        default_group_permissions
    )
    default_group_permissions_to_add = default_group_permissions.difference(
        current_default_group_permissions
    )
    for permission in default_group_permissions_to_add:
        assign_perm(permission, default_group)
    for permission in default_group_permissions_to_remove:
        remove_perm(permission, default_group)

    # Superadmins group
    superadmins_group = get_superadmins_group()
    superadmins_group_permissions = get_superadmins_group_permissions()
    current_superadmins_group_permissions = superadmins_group.permissions.all()
    superadmins_group_permissions_to_remove = (
        current_superadmins_group_permissions.difference(superadmins_group_permissions)
    )
    superadmins_group_permissions_to_add = superadmins_group_permissions.difference(
        current_superadmins_group_permissions
    )
    for permission in superadmins_group_permissions_to_add:
        assign_perm(permission, superadmins_group)
    for permission in superadmins_group_permissions_to_remove:
        remove_perm(permission, superadmins_group)


@app.task(name="apps.deploys.tasks.reassign_projects_permissions")
def reassign_projects_permissions():
    """Reassign permissions for all projects."""
    owners_permissions = Project.get_default_owners_permissions()
    reviewers_permissions = Project.get_default_reviewers_permissions()
    members_permissions = Project.get_default_members_permissions()
    Project.batch_reassign_permissions(
        roles_permissions=(
            (GroupData.Role.OWNERS, owners_permissions),
            (GroupData.Role.OWNER_GROUPS, owners_permissions),
            (GroupData.Role.REVIEWERS, reviewers_permissions),
            (GroupData.Role.REVIEWER_GROUPS, reviewers_permissions),
            (GroupData.Role.MEMBERS, members_permissions),
            (GroupData.Role.MEMBER_GROUPS, members_permissions),
        ),
    )


@app.task(name="apps.deploys.tasks.reassign_people_groups_permissions")
def reassign_people_groups_permissions():
    """Reassign permissions for all people groups."""
    leaders_permissions = PeopleGroup.get_default_leaders_permissions()
    managers_permissions = PeopleGroup.get_default_managers_permissions()
    members_permissions = PeopleGroup.get_default_members_permissions()
    PeopleGroup.batch_reassign_permissions(
        roles_permissions=(
            (GroupData.Role.LEADERS, leaders_permissions),
            (GroupData.Role.MANAGERS, managers_permissions),
            (GroupData.Role.MEMBERS, members_permissions),
        ),
    )


@app.task(name="apps.deploys.tasks.reassign_organizations_permissions")
def reassign_organizations_permissions():
    """Reassign permissions for all organizations."""
    admins_permissions = Organization.get_default_admins_permissions()
    facilitators_permissions = Organization.get_default_facilitators_permissions()
    users_permissions = Organization.get_default_users_permissions()
    Organization.batch_reassign_permissions(
        roles_permissions=(
            (GroupData.Role.ADMINS, admins_permissions),
            (GroupData.Role.FACILITATORS, facilitators_permissions),
            (GroupData.Role.USERS, users_permissions),
        ),
    )
    # Additionally, setup global admin permissions
    for organization in Organization.objects.all():
        organization.setup_group_global_permissions(
            organization.get_admins(), organization.get_global_admins_permissions()
        )
