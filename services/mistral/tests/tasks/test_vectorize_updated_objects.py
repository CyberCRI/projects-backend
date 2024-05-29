from unittest.mock import call, patch

from apps.commons.test import JwtAPITestCase
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.tasks import _vectorize_updated_objects


class VectorizeUpdatedObjectsTest(JwtAPITestCase):
    @patch("services.mistral.models.Embedding.set_embedding")
    def test_vectorize_updated_objects(self, mocked_vectorize):
        mocked_vectorize.return_value = None

        ProjectEmbeddingFactory()
        UserEmbeddingFactory()

        project_embdedding = ProjectEmbeddingFactory()
        project_embdedding.prompt_hashcode = project_embdedding.hash_prompt()
        project_embdedding.save()

        user_embedding = UserEmbeddingFactory()
        user_embedding.prompt_hashcode = user_embedding.hash_prompt()
        user_embedding.save()

        _vectorize_updated_objects()
        mocked_vectorize.assert_has_calls([call(None), call(None)])
