from unittest.mock import call, patch

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory
from services.mistral.tasks import update_queued_embeddings


class MixpanelServiceTestCase(JwtAPITestCase):
    @patch("services.mistral.models.Embedding._vectorize")
    def test_update_queued_embeddings(self, mocked):
        mocked.return_value = None

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

        update_queued_embeddings()
        mocked.assert_has_calls([call(None), call(None)])
