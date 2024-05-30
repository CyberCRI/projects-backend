from unittest.mock import call, patch

from apps.commons.test import JwtAPITestCase
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.tasks import _vectorize_updated_objects


class VectorizeUpdatedObjectsTest(JwtAPITestCase):
    @patch("services.mistral.models.UserEmbedding.vectorize")
    @patch("services.mistral.models.ProjectEmbedding.vectorize")
    def test_vectorize_updated_objects(
        self, mocked_project_vectorize, mocked_user_vectorize
    ):
        mocked_user_vectorize.return_value = None
        mocked_project_vectorize.return_value = None

        ProjectEmbeddingFactory()
        UserEmbeddingFactory()

        project_embdedding = ProjectEmbeddingFactory()
        project_embdedding.prompt_hashcode = project_embdedding.hash_prompt()
        project_embdedding.save()

        _vectorize_updated_objects()
        mocked_user_vectorize.assert_has_calls([call()])
        mocked_project_vectorize.assert_has_calls([call()])
