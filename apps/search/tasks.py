from django.utils import timezone

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.projects.models import Project
from projects.celery import app

from .models import SearchObject


@app.task(name="apps.search.tasks.update_or_create_user_search_object")
def update_or_create_user_search_object_task(instance_pk):
    _update_or_create_user_search_object_task(instance_pk)


def _update_or_create_user_search_object_task(instance_pk):
    """Create the associated search object at people group's creation."""
    user = ProjectUser.objects.filter(pk=instance_pk)
    if user.exists():
        user = user.get()
        search_objects = SearchObject.objects.filter(
            type=SearchObject.SearchObjectType.USER, user=user
        )
        while search_objects.count() > 1:
            search_objects.last().delete()
        search_object, _ = SearchObject.objects.update_or_create(
            user=user,
            type=SearchObject.SearchObjectType.USER,
            defaults={"last_update": timezone.localtime(timezone.now())},
        )
        search_object.save()


@app.task(name="apps.search.tasks.update_or_create_project_search_object")
def update_or_create_project_search_object_task(instance_pk):
    _update_or_create_project_search_object_task(instance_pk)


def _update_or_create_project_search_object_task(instance_pk):
    """Create the associated search object at people group's creation."""
    project = Project.objects.filter(pk=instance_pk)
    if project.exists():
        project = project.get()
        search_objects = SearchObject.objects.filter(
            type=SearchObject.SearchObjectType.PROJECT, project=project
        )
        while search_objects.count() > 1:
            search_objects.last().delete()
        search_object, _ = SearchObject.objects.update_or_create(
            project=project,
            type=SearchObject.SearchObjectType.PROJECT,
            defaults={"last_update": timezone.localtime(timezone.now())},
        )
        search_object.save()


@app.task(name="apps.search.tasks.delete_project_search_object")
def delete_project_search_object_task(instance_pk):
    _delete_project_search_object_task(instance_pk)


def _delete_project_search_object_task(instance_pk):
    """Delete the associated search object at project's deletion."""
    search_objects = SearchObject.objects.filter(project__pk=instance_pk)
    if search_objects.exists():
        search_objects.delete()


@app.task(name="apps.search.tasks.update_or_create_people_group_search_object")
def update_or_create_people_group_search_object_task(instance_pk):
    _update_or_create_people_group_search_object_task(instance_pk)


def _update_or_create_people_group_search_object_task(instance_pk):
    """Create the associated search object at people group's creation."""
    people_group = PeopleGroup.objects.filter(pk=instance_pk)
    if people_group.exists():
        people_group = people_group.get()
        search_objects = SearchObject.objects.filter(
            type=SearchObject.SearchObjectType.PEOPLE_GROUP, people_group=people_group
        )
        while search_objects.count() > 1:
            search_objects.last().delete()
        search_object, _ = SearchObject.objects.update_or_create(
            people_group=people_group,
            type=SearchObject.SearchObjectType.PEOPLE_GROUP,
            defaults={"last_update": timezone.localtime(timezone.now())},
        )
        search_object.save()
