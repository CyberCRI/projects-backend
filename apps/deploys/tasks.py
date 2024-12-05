from django.core.management import call_command
from guardian.shortcuts import assign_perm

from apps.accounts.utils import (
    get_default_group,
    get_default_group_permissions,
    get_superadmins_group,
    get_superadmins_group_permissions,
)
from apps.commons.models import PermissionsSetupModel
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
    default_group = get_default_group()
    default_group.permissions.clear()
    for permission in get_default_group_permissions():
        assign_perm(permission, default_group)

    superadmins_group = get_superadmins_group()
    superadmins_group.permissions.clear()
    for permission in get_superadmins_group_permissions():
        assign_perm(permission, superadmins_group)


@app.task
def instance_groups_permissions():
    permissions_setup_models = PermissionsSetupModel.__subclasses__()
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
