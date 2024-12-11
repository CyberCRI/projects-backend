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
    """
    Base class for post deploy tasks

    All subclasses of this class will create a PostDeployProcess object
    in the database with the attributes defined in the subclass.

    These processes are executed by the PostDeployProcess.deploy() method.

    Attributes:
    task_name: str
        Name of the task, must be unique
    priority: int
        Priority of the task, lower numbers will be executed first
    task: Callable[[int], None]
        Task to be executed
    run_in_tests: bool = False
        If the task should be executed in the tests environment
    run_in_celery: bool = True
        If the task should be executed in celery
    sleep_time: int = 30
        Time (in minutes) during which the task should not be executed again
        if the deploy() method is called multiple times in a short period.
    """

    task_name: str
    priority: int
    task: Callable[[int], None]
    run_in_tests: bool = False
    run_in_celery: bool = True
    sleep_time: int = 30  # in minutes

    @classmethod
    def run(cls):
        """Run the task"""
        return cls.task()

    @classmethod
    def celery_run(cls):
        """Run the task in celery"""
        return cls.task.delay()

    def get_progress(self):
        """Get the current progress of the task"""
        return None  # noqa: R501


class Migrate(PostDeployTask):
    """Apply all migrations"""

    task_name = "migrate"
    priority = 1
    task = migrate
    run_in_tests = True
    run_in_celery = False
    sleep_time = 0


class BaseGroupsPermissions(PostDeployTask):
    """Assign permissions to the default and superadmins groups"""

    task_name = "base_groups_permissions"
    priority = 2
    task = base_groups_permissions
    run_in_tests = True


class AlgoliaReindex(PostDeployTask):
    """Reindex all searchable models in Algolia"""

    task_name = "algolia_reindex"
    priority = 3
    task = algolia_reindex_task


class InstanceGroupsPermissions(PostDeployTask):
    """
    Assign permissions to the default groups of all models that inherit from
    PermissionsSetupModel :
    - Project
    - PeopleGroup
    - Organization
    """

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
    """If a user has redundant roles, remove the less powerful ones"""

    task_name = "remove_duplicated_roles"
    priority = 5
    task = remove_duplicated_roles


# class CreateDefaultTagClassifications(PostDeployTask):  # noqa
#     task_name = "default_tag_classifications"  # noqa
#     priority = 6  # noqa
#     task = default_tag_classifications  # noqa
