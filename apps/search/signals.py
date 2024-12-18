from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.projects.models import Project

from .tasks import (
    delete_project_search_object_task,
    update_or_create_people_group_search_object_task,
    update_or_create_project_search_object_task,
    update_or_create_user_search_object_task,
)

# User index update signals


@receiver(post_save, sender="accounts.ProjectUser")
def update_search_object_on_user_save(sender, instance, created, **kwargs):
    """Create the associated search object at user's creation."""
    if isinstance(instance, ProjectUser):
        if created:
            update_or_create_user_search_object_task(instance.pk)
        else:
            update_or_create_user_search_object_task.delay(instance.pk)


@receiver(post_save, sender="skills.Skill")
def update_search_object_on_user_skill_save(sender, instance, created, **kwargs):
    """Create the associated search object at user's creation."""
    if isinstance(instance.user, ProjectUser):
        update_or_create_user_search_object_task.delay(instance.user.pk)


@receiver(post_save, sender="accounts.PrivacySettings")
def update_search_object_on_user_privacy_settings_save(
    sender, instance, created, **kwargs
):
    """Create the associated search object at user's creation."""
    if isinstance(instance.user, ProjectUser):
        update_or_create_user_search_object_task.delay(instance.user.pk)


@receiver(m2m_changed, sender=ProjectUser.groups.through)
def update_search_object_on_user_role_change(sender, instance, action, **kwargs):
    """Create the associated search object at user's creation."""
    if isinstance(instance, ProjectUser) and action in ["post_add", "post_remove"]:
        update_or_create_user_search_object_task.delay(instance.pk)


# Project index update signals


@receiver(post_save, sender="projects.Project")
def update_search_object_on_project_save(sender, instance, created, **kwargs):
    """Create the associated search object at project's creation."""
    if isinstance(instance, Project):
        if created and instance.deleted_at is None:
            update_or_create_project_search_object_task(instance.pk)
        else:
            if instance.deleted_at is not None:
                delete_project_search_object_task.delay(instance.pk)
            else:
                update_or_create_project_search_object_task.delay(instance.pk)


@receiver(m2m_changed, sender=Project.organizations.through)
def update_search_object_on_project_organization_change(
    sender, instance, action, **kwargs
):
    """Create the associated search object at project's creation."""
    if (
        isinstance(instance, Project)
        and action in ["post_add", "post_remove"]
        and instance.deleted_at is None
    ):
        update_or_create_project_search_object_task.delay(instance.pk)


@receiver(m2m_changed, sender=Project.categories.through)
def update_search_object_on_project_category_change(sender, instance, action, **kwargs):
    """Create the associated search object at project's creation."""
    if (
        isinstance(instance, Project)
        and action in ["post_add", "post_remove"]
        and instance.deleted_at is None
    ):
        update_or_create_project_search_object_task.delay(instance.pk)


@receiver(m2m_changed, sender=Project.tags.through)
def update_search_object_on_project_tags_change(sender, instance, action, **kwargs):
    """Create the associated search object at project's creation."""
    if (
        isinstance(instance, Project)
        and action in ["post_add", "post_remove"]
        and instance.deleted_at is None
    ):
        update_or_create_project_search_object_task.delay(instance.pk)


# People group index update signals


@receiver(post_save, sender="accounts.PeopleGroup")
def update_or_create_people_group_search_object(sender, instance, created, **kwargs):
    """Create the associated search object at people group's creation."""
    if isinstance(instance, PeopleGroup):
        if created:
            update_or_create_people_group_search_object_task(instance.pk)
        else:
            update_or_create_people_group_search_object_task.delay(instance.pk)
