from django.utils import timezone

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.projects.models import Project
from projects.celery import app

from .models import SearchObject


@app.task(name="apps.search.tasks.update_or_create_user_search_object")
def update_or_create_user_search_object_task(instance_pk):
    """Create the associated search object at people group's creation."""
    user = ProjectUser.objects.get(pk=instance_pk)
    search_object, _ = SearchObject.objects.update_or_create(
        user=user,
        type=SearchObject.SearchObjectType.USER,
        defaults={"last_update": timezone.localtime(timezone.now())},
    )
    search_object.save()


@app.task(name="apps.search.tasks.update_or_create_project_search_object")
def update_or_create_project_search_object_task(instance_pk):
    """Create the associated search object at people group's creation."""
    project = Project.objects.get(pk=instance_pk)
    search_object, _ = SearchObject.objects.update_or_create(
        project=project,
        type=SearchObject.SearchObjectType.PROJECT,
        defaults={"last_update": timezone.localtime(timezone.now())},
    )
    search_object.save()


@app.task(name="apps.search.tasks.update_or_create_people_group_search_object")
def update_or_create_people_group_search_object_task(instance_pk):
    """Create the associated search object at people group's creation."""
    people_group = PeopleGroup.objects.get(pk=instance_pk)
    search_object, _ = SearchObject.objects.update_or_create(
        people_group=people_group,
        type=SearchObject.SearchObjectType.PEOPLE_GROUP,
        defaults={"last_update": timezone.localtime(timezone.now())},
    )
    search_object.save()
