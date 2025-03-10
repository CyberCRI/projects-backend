from django.core.management import call_command
from guardian.shortcuts import assign_perm, remove_perm

from apps.accounts.utils import (
    get_default_group,
    get_default_group_permissions,
    get_superadmins_group,
    get_superadmins_group_permissions,
)
from apps.commons.mixins import HasPermissionsSetup
from apps.skills.models import TagClassification
from projects.celery import app


def migrate():
    call_command("migrate")


@app.task
def rebuild_index():
    """
    python manage.py opensearch index rebuild --force
    """
    call_command("update_or_rebuild_index")


@app.task
def base_groups_permissions():
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


@app.task
def instance_groups_permissions():
    permissions_setup_models = HasPermissionsSetup.__subclasses__()
    for permissions_setup_model in permissions_setup_models:
        permissions_setup_model.objects.all().update(permissions_up_to_date=False)
    for permissions_setup_model in permissions_setup_models:
        for instance in permissions_setup_model.objects.filter(
            permissions_up_to_date=False
        ):
            instance.setup_permissions(trigger_indexation=False)


@app.task
def default_tag_classifications():
    for classification_type in TagClassification.TagClassificationType.values:
        if classification_type != TagClassification.TagClassificationType.CUSTOM:
            TagClassification.get_or_create_default_classification(
                classification_type=classification_type
            )
