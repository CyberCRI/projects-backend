from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import ProjectUser
from apps.projects.models import Project

from .models import ProjectEmbedding, UserEmbedding


@receiver(post_save, sender=Project)
def queue_or_create_project_embedding(sender, instance: Project, created, **kwargs):
    ProjectEmbedding.queue_or_create(item=instance)


@receiver(post_save, sender=ProjectUser)
def queue_or_create_user_embedding(sender, instance: ProjectUser, created, **kwargs):
    UserEmbedding.queue_or_create(item=instance)
