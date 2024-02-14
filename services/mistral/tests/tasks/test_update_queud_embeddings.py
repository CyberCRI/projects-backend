from unittest.mock import call, patch

from apps.commons.test import JwtAPITestCase
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.tasks import update_queued_embeddings


class MixpanelServiceTestCase(JwtAPITestCase):
    @patch("services.mistral.models.Embedding._vectorize")
    def test_update_queued_embeddings(self, mocked):
        mocked.return_value = None
        ProjectEmbeddingFactory(queued_for_update=True)
        UserEmbeddingFactory(queued_for_update=True)
        ProjectEmbeddingFactory(queued_for_update=False)
        UserEmbeddingFactory(queued_for_update=False)
        update_queued_embeddings()
        mocked.assert_has_calls([call(None), call(None)])
