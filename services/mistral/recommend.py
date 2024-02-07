from apps.misc.models import WikipediaTag
from apps.projects.models import Project
from apps.accounts.models import ProjectUser
from pgvector.django import CosineDistance

from .interface import MistralService


def get_recommended_projects_for_query(query: str):
    query_embedding = MistralService.get_embeddings(query)
    return Project.objects.filter(
        summary_embedding__isnull=False,
    ).order_by(
        CosineDistance('summary_embedding', query_embedding)
    )[:5]


def get_recommended_projects_for_project(project: Project):
    if project.summary_embedding is None:
        return []
    return Project.objects.filter(
        summary_embedding__isnull=False,
    ).order_by(
        CosineDistance('summary_embedding', project.summary_embedding)
    )[:5]


def get_recommended_projects_for_user(user: ProjectUser):
    if user.summary_embedding is None:
        return []
    return Project.objects.exclude(groups__users=user).filter(
        summary_embedding__isnull=False,
    ).annotate(distance=CosineDistance('summary_embedding', user.summary_embedding)).order_by("distance")[:15]


def get_recommended_users_for_project(project: Project):
    if project.summary_embedding is None:
        return []
    return ProjectUser.objects.filter(
        summary_embedding__isnull=False,
    ).order_by(
        CosineDistance('summary_embedding', project.summary_embedding)
    )[:5]


def get_recommended_users_for_wikipedia_tag(wikipedia_tag):
    if wikipedia_tag.embedding is None:
        return []
    recommended_tags = WikipediaTag.objects.filter(
        embedding__isnull=False,
    ).order_by(
        CosineDistance('embedding', wikipedia_tag.embedding)
    )[:5]
    return ProjectUser.objects.filter(
        skills__wikipedia_tag__in=recommended_tags
    ).distinct()[:5]