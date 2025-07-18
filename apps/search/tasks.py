from django.db.models import Count

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.utils import clear_memory
from apps.projects.models import Project
from projects.celery import app


@app.task(name="apps.search.tasks.clean_duplicate_search_objects")
@clear_memory
def clean_duplicate_search_objects():
    """Clean duplicate SearchObject instances."""
    user_duplicates = ProjectUser.objects.annotate(
        search_objects=Count("search_object")
    ).filter(search_objects__gt=1)
    for user in user_duplicates:
        user.search_object.exclude(id=user.search_object.first().id).delete()
    group_duplicates = PeopleGroup.objects.annotate(
        search_objects=Count("search_object")
    ).filter(search_objects__gt=1)
    for group in group_duplicates:
        group.search_object.exclude(id=group.search_object.first().id).delete()
    project_duplicates = Project.objects.annotate(
        search_objects=Count("search_object")
    ).filter(search_objects__gt=1)
    for project in project_duplicates:
        project.search_object.exclude(id=project.search_object.first().id).delete()
