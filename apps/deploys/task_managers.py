from typing import Callable

from .tasks import (
    migrate,
    reassign_base_groups_permissions,
    reassign_organizations_permissions,
    reassign_people_groups_permissions,
    reassign_projects_permissions,
    rebuild_index,
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
    task = reassign_base_groups_permissions
    run_in_tests = True


class OrganizationsGroupsPermissions(PostDeployTask):
    """Reassign permissions to the default groups of all organizations"""

    task_name = "organization_groups_permissions"
    priority = 3
    task = reassign_organizations_permissions


class PeopleGroupGroupsPermissions(PostDeployTask):
    """Reassign permissions to the default groups of all people groups"""

    task_name = "peoplegroup_groups_permissions"
    priority = 4
    task = reassign_people_groups_permissions


class ProjectGroupsPermissions(PostDeployTask):
    """Reassign permissions to the default groups of all projects"""

    task_name = "project_groups_permissions"
    priority = 5
    task = reassign_projects_permissions


class RebuildIndex(PostDeployTask):
    """Reindex all searchable models in OpenSearch"""

    task_name = "rebuild_index"
    priority = 6
    task = rebuild_index


# class CreateDefaultTagClassifications(PostDeployTask):  # noqa
#     task_name = "default_tag_classifications"  # noqa
#     priority = 6  # noqa
#     task = default_tag_classifications  # noqa
