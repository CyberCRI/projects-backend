from typing import Callable

from django.conf import settings

from apps.commons.db.abc import PermissionsSetupModel

from .tasks import (
    algolia_reindex_task,
    base_groups_permissions,
    instance_groups_permissions,
    remove_duplicated_roles,
)


class PostDeployTask:
    task_name: str
    priority: int
    task: Callable[[int], None]
    run_in_tests: bool = True

    @classmethod
    def run(cls):
        if settings.ENVIRONMENT == "test":
            cls.task()
        return cls.task.delay()

    def get_progress(self):
        return None


class BaseGroupsPermissions(PostDeployTask):
    task_name = "base_groups_permissions"
    priority = 1
    task = base_groups_permissions


class AlgoliaReindex(PostDeployTask):
    task_name = "algolia_reindex"
    priority = 2
    task = algolia_reindex_task
    run_in_tests = False


class InstanceGroupsPermissions(PostDeployTask):
    task_name = "instance_groups_permissions"
    priority = 3
    task = instance_groups_permissions

    def get_progress(self):
        models = PermissionsSetupModel.__subclasses__()
        updated_objects = sum(
            [m.objects.filter(permissions_up_to_date=True).count() for m in models]
        )
        total_objects = sum([m.objects.count() for m in models])
        return f"{str(round((updated_objects / total_objects)*100, 2))}%"


class RemoveDuplicatedRoles(PostDeployTask):
    task_name = "remove_duplicated_roles"
    priority = 4
    task = remove_duplicated_roles
