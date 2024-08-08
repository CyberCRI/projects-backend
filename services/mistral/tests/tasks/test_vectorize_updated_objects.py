from unittest.mock import call, patch

from apps.commons.test import JwtAPITestCase
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.models import EmbeddingError
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

    @patch("services.mistral.models.UserEmbedding.set_embedding")
    def test_user_embedding_error(self, mocked_user_vectorize):
        mocked_user_vectorize.side_effect = ValueError("Test error")
        embedding = UserEmbeddingFactory()
        _vectorize_updated_objects()
        mocked_user_vectorize.assert_has_calls([call()])
        error = EmbeddingError.objects.filter(
            item_id=embedding.item.id,
            item_type="ProjectUser",
        )
        self.assertTrue(error.exists())
        error = error.get()
        self.assertEqual(error.error, "ValueError")
        self.assertIn("ValueError: Test error", error.traceback)

    @patch("services.mistral.models.ProjectEmbedding.set_embedding")
    def test_project_embedding_error(self, mocked_project_vectorize):
        mocked_project_vectorize.side_effect = ValueError("Test error")
        embedding = ProjectEmbeddingFactory()
        _vectorize_updated_objects()
        mocked_project_vectorize.assert_has_calls([call()])
        error = EmbeddingError.objects.filter(
            item_id=embedding.item.id,
            item_type="Project",
        )
        self.assertTrue(error.exists())
        error = error.get()
        self.assertEqual(error.error, "ValueError")
        self.assertIn("ValueError: Test error", error.traceback)
