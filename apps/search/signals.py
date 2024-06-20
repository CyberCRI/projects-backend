from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SearchObject


@receiver(post_save, sender="accounts.ProjectUser")
def create_user_search_object(sender, instance, created, **kwargs):
    """Create the associated search object at user's creation."""
    search_object, _ = SearchObject.objects.get_or_create(
        user=instance, type=SearchObject.SearchObjectType.USER
    )
    search_object.save()


@receiver(post_save, sender="projects.Project")
def create_project_search_object(sender, instance, created, **kwargs):
    """Create the associated search object at project's creation."""
    search_object, _ = SearchObject.objects.get_or_create(
        project=instance, type=SearchObject.SearchObjectType.PROJECT
    )
    search_object.save()


@receiver(post_save, sender="accounts.PeopleGroup")
def create_people_group_search_object(sender, instance, created, **kwargs):
    """Create the associated search object at people group's creation."""
    search_object, _ = SearchObject.objects.get_or_create(
        people_group=instance, type=SearchObject.SearchObjectType.PEOPLE_GROUP
    )
    search_object.save()
