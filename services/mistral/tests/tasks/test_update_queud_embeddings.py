from unittest.mock import call, patch

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory
from services.mistral.tasks import (
    _update_queued_embeddings,
    queue_or_create_project_embedding_task,
    queue_or_create_user_embedding_task,
)


class MixpanelServiceTestCase(JwtAPITestCase):
    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    @patch("services.mistral.models.Embedding._vectorize")
    def test_update_queued_embeddings(
        self, mocked_vectorize, mocked_user_delay, mocked_project_delay
    ):
        mocked_vectorize.return_value = None
        mocked_user_delay.side_effect = queue_or_create_user_embedding_task
        mocked_project_delay.side_effect = queue_or_create_project_embedding_task

        queued_project = ProjectFactory()
        queued_project.embedding.queued_for_update = True
        queued_project.save()

        queued_user = UserFactory()
        queued_user.embedding.queued_for_update = True
        queued_user.save()

        user = UserFactory()
        user.embedding.queued_for_update = False
        user.save()

        project = ProjectFactory()
        project.embedding.queued_for_update = False
        project.save()

        _update_queued_embeddings()
        mocked_vectorize.assert_has_calls([call(None), call(None)])
