from django.core.management import call_command
from guardian.shortcuts import assign_perm

from apps.accounts.utils import (
    get_default_group,
    get_default_group_permissions,
    get_superadmins_group,
    get_superadmins_group_permissions,
)
from apps.commons.models import PermissionsSetupModel
from projects.celery import app


@app.task
def algolia_reindex_task():
    call_command("algolia_reindex")


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
            instance.setup_permissions()


@app.task
def remove_duplicated_roles():
    permissions_setup_models = PermissionsSetupModel.__subclasses__()
    for permissions_setup_model in permissions_setup_models:
        for instance in permissions_setup_model.objects.all():
            instance.remove_duplicated_roles()
