from apps.accounts.models import ProjectUser
from apps.projects.models import Project
from projects.celery import app

from .models import ProjectEmbedding, UserEmbedding


@app.task
def update_queued_embeddings():
    _update_queued_embeddings()


def _update_queued_embeddings():
    project_embeddings = ProjectEmbedding.objects.filter(queued_for_update=True)
    user_embeddings = UserEmbedding.objects.filter(queued_for_update=True)
    for embedding in list(project_embeddings) + list(user_embeddings):
        embedding.vectorize()


@app.task
def queue_or_create_project_embedding_task(item_id: str):
    _queue_or_create_project_embedding_task(item_id)


def _queue_or_create_project_embedding_task(item_id: str):
    project = Project.objects.get(id=item_id)
    ProjectEmbedding.queue_or_create(item=project)


@app.task
def queue_or_create_user_embedding_task(item_id: int):
    _queue_or_create_user_embedding_task(item_id)


def _queue_or_create_user_embedding_task(item_id: int):
    user = ProjectUser.objects.get(id=item_id)
    UserEmbedding.queue_or_create(item=user)
