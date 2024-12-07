from typing import Callable

from apps.commons.models import PermissionsSetupModel

from .tasks import (
    algolia_reindex_task,
    base_groups_permissions,
    instance_groups_permissions,
    migrate,
    remove_duplicated_roles,
)


class PostDeployTask:
    task_name: str
    priority: int
    task: Callable[[int], None]
    run_in_tests: bool = False
    run_in_celery: bool = True

    @classmethod
    def run(cls):
        return cls.task()

    @classmethod
    def celery_run(cls):
        return cls.task.delay()

    def get_progress(self):
        return None


class Migrate(PostDeployTask):
    task_name = "migrate"
    priority = 1
    task = migrate
    run_in_tests = True
    run_in_celery = False


class BaseGroupsPermissions(PostDeployTask):
    task_name = "base_groups_permissions"
    priority = 2
    task = base_groups_permissions
    run_in_tests = True


class AlgoliaReindex(PostDeployTask):
    task_name = "algolia_reindex"
    priority = 3
    task = algolia_reindex_task


class InstanceGroupsPermissions(PostDeployTask):
    task_name = "instance_groups_permissions"
    priority = 4
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
    priority = 5
    task = remove_duplicated_roles


# class CreateDefaultTagClassifications(PostDeployTask):  # noqa
#     task_name = "default_tag_classifications"  # noqa
#     priority = 6  # noqa
#     task = default_tag_classifications  # noqa
