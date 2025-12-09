import logging

from apps.commons.utils import clear_memory
from projects.celery import app

from .models import DocumentEmbedding, MistralEmbedding, ProjectEmbedding, UserEmbedding

logger = logging.getLogger(__name__)


@app.task(name="services.mistral.tasks.vectorize_updated_objects")
def vectorize_updated_objects():
    _vectorize_updated_objects()


@clear_memory
def _vectorize_objects(model_embedding: MistralEmbedding):
    related_model = model_embedding.item.field.related_model
    related_query_name = model_embedding.item.field.related_query_name()

    for obj in (
        related_model.objects.select_related(related_query_name).all().iterator()
    ):
        embedding = getattr(obj, related_query_name, None)
        # embedding not exists
        if embedding is None:
            embedding = model_embedding(item=obj)
        embedding.vectorize()


def _vectorize_updated_objects():
    _vectorize_objects(ProjectEmbedding)
    _vectorize_objects(UserEmbedding)
    _vectorize_objects(DocumentEmbedding)
