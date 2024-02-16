from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import ProjectUser
from apps.projects.models import Project

from .tasks import (
    queue_or_create_project_embedding_task,
    queue_or_create_user_embedding_task,
)


@receiver(post_save, sender=Project)
def queue_or_create_project_embedding(sender, instance: Project, created, **kwargs):
    if getattr(instance, "queue_for_embedding", True):
        queue_or_create_project_embedding_task.delay(item_id=instance.id)


@receiver(post_save, sender=ProjectUser)
def queue_or_create_user_embedding(sender, instance: ProjectUser, created, **kwargs):
    if getattr(instance, "queue_for_embedding", True):
        queue_or_create_user_embedding_task.delay(item_id=instance.id)
