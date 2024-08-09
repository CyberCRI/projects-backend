import logging

from apps.accounts.models import ProjectUser
from apps.projects.models import Project
from projects.celery import app

from .models import ProjectEmbedding, UserEmbedding

logger = logging.getLogger(__name__)


@app.task
def vectorize_updated_objects():
    _vectorize_updated_objects()


def _vectorize_updated_objects():
    projects = Project.objects.all()
    users = ProjectUser.objects.all()
    for project in projects:
        embedding, _ = ProjectEmbedding.objects.get_or_create(item=project)
        embedding.vectorize()
    for user in users:
        embedding, _ = UserEmbedding.objects.get_or_create(item=user)
        embedding.vectorize()
