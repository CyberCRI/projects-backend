from unittest.mock import patch

from faker import Faker

from apps.accounts.factories import SkillFactory, UserFactory
from apps.commons.test import JwtAPITestCase
from services.mistral.tasks import queue_or_create_user_embedding_task
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class UserEmbeddingVisibilityTestCase(JwtAPITestCase):
    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_set_visibility_with_personal_description(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(
            personal_description=faker.text(), professional_description=""
        )
        user.embedding.set_visibility()
        assert user.embedding.is_visible

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_set_visibility_with_professional_description(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(
            personal_description="", professional_description=faker.text()
        )
        user.embedding.set_visibility()
        assert user.embedding.is_visible

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_set_visibility_with_skills(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(personal_description="", professional_description="")
        SkillFactory(user=user, level=3)
        user.embedding.set_visibility()
        assert user.embedding.is_visible

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_set_visibility_not_visible(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(personal_description="", professional_description="")
        SkillFactory(user=user, level=2)
        user.embedding.set_visibility()
        assert not user.embedding.is_visible


class VectorizeUserTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_personal_description(
        self, mocked_embeddings, mocked_chat, mocked_delay
    ):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(
            personal_description=faker.text(), professional_description=""
        )
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            embedding
        )
        user.embedding.vectorize()
        assert user.embedding.is_visible
        assert user.embedding.embedding == embedding
        assert user.embedding.prompt_hashcode != ""

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_professional_description(
        self, mocked_embeddings, mocked_chat, mocked_delay
    ):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(
            personal_description="", professional_description=faker.text()
        )
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            embedding
        )
        user.embedding.vectorize()
        assert user.embedding.is_visible
        assert user.embedding.embedding == embedding
        assert user.embedding.prompt_hashcode != ""

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_skills(self, mocked_embeddings, mocked_chat, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(personal_description="", professional_description="")
        SkillFactory(user=user, level=3)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            embedding
        )
        user.embedding.vectorize()
        assert user.embedding.is_visible
        assert user.embedding.embedding == embedding
        assert user.embedding.prompt_hashcode != ""

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_not_visible(self, mocked_embeddings, mocked_chat, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(personal_description="", professional_description="")
        SkillFactory(user=user, level=2)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            embedding
        )
        user.embedding.vectorize()
        assert not user.embedding.is_visible
        assert user.embedding.embedding is not None
        assert user.embedding.prompt_hashcode != ""


class UserEmbeddingTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_get_summary_chat_system(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(professional_description=faker.text())
        response = user.embedding.get_summary_chat_system()
        assert all(isinstance(x, str) for x in response)

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_get_summary_chat_prompt(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(professional_description=faker.text())
        response = user.embedding.get_summary_chat_prompt()
        assert all(isinstance(x, str) for x in response)

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_queue_or_create_new_user(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory()
        user.refresh_from_db()
        assert user.embedding.queued_for_update is True

    @patch("services.mistral.signals.queue_or_create_user_embedding_task.delay")
    def test_queue_or_create_existing_user(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_user_embedding_task
        user = UserFactory(professional_description=faker.text())
        user.embedding.queued_for_update = False
        user.embedding.save()
        user.description = faker.text()
        user.save()
        user.refresh_from_db()
        assert user.embedding.queued_for_update is True
