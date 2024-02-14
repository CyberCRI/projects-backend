from django.conf import settings

from projects.celery import app

from .models import ProjectEmbedding, UserEmbedding


@app.task
def update_queued_embeddings():
    if settings.MISTRAL_AUTO_UPDATE:
        _update_queued_embeddings()


def _update_queued_embeddings():
    project_embeddings = ProjectEmbedding.objects.filter(queued_for_update=True)
    user_embeddings = UserEmbedding.objects.filter(queued_for_update=True)
    for embedding in list(project_embeddings) + list(user_embeddings):
        embedding.vectorize()
