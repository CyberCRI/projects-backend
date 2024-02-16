from unittest.mock import patch

from faker import Faker

from apps.accounts.factories import SkillFactory, UserFactory
from apps.commons.test import JwtAPITestCase
from services.mistral.factories import UserEmbeddingFactory
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class UserEmbeddingVisibilityTestCase(JwtAPITestCase):
    def test_set_visibility_with_personal_description(self):
        user = UserFactory(
            personal_description=faker.text(), professional_description=""
        )
        embedding = UserEmbeddingFactory(item=user)
        embedding.set_visibility()
        assert embedding.is_visible

    def test_set_visibility_with_professional_description(self):
        user = UserFactory(
            personal_description="", professional_description=faker.text()
        )
        embedding = UserEmbeddingFactory(item=user)
        embedding.set_visibility()
        assert embedding.is_visible

    def test_set_visibility_with_skills(self):
        user = UserFactory(personal_description="", professional_description="")
        embedding = UserEmbeddingFactory(item=user)
        SkillFactory(user=user, level=3)
        embedding.set_visibility()
        assert embedding.is_visible

    def test_set_visibility_not_visible(self):
        user = UserFactory(personal_description="", professional_description="")
        embedding = UserEmbeddingFactory(item=user)
        SkillFactory(user=user, level=2)
        embedding.set_visibility()
        assert not embedding.is_visible


class VectorizeUserTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_personal_description(self, mocked_embeddings, mocked_chat):
        user = UserFactory(
            personal_description=faker.text(), professional_description=""
        )
        embedding = UserEmbeddingFactory(item=user)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        vector = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        embedding.vectorize()
        assert embedding.is_visible
        assert embedding.embedding == vector
        assert embedding.prompt_hashcode != ""

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_professional_description(
        self, mocked_embeddings, mocked_chat
    ):
        user = UserFactory(
            personal_description="", professional_description=faker.text()
        )
        embedding = UserEmbeddingFactory(item=user)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        vector = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        embedding.vectorize()
        assert embedding.is_visible
        assert embedding.embedding == vector
        assert embedding.prompt_hashcode != ""

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_skills(self, mocked_embeddings, mocked_chat):
        user = UserFactory(personal_description="", professional_description="")
        embedding = UserEmbeddingFactory(item=user)
        SkillFactory(user=user, level=3)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        vector = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        embedding.vectorize()
        assert embedding.is_visible
        assert embedding.embedding == vector
        assert embedding.prompt_hashcode != ""

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_not_visible(self, mocked_embeddings, mocked_chat):
        user = UserFactory(personal_description="", professional_description="")
        embedding = UserEmbeddingFactory(item=user)
        SkillFactory(user=user, level=2)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        vector = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        embedding.vectorize()
        assert not embedding.is_visible
        assert embedding.embedding is not None
        assert embedding.prompt_hashcode != ""


class UserEmbeddingTestCase(JwtAPITestCase, MistralTestCaseMixin):
    def test_get_summary_chat_system(self):
        user = UserFactory(professional_description=faker.text())
        embedding = UserEmbeddingFactory(item=user)
        response = embedding.get_summary_chat_system()
        assert all(isinstance(x, str) for x in response)

    def test_get_summary_chat_prompt(self):
        user = UserFactory(professional_description=faker.text())
        embedding = UserEmbeddingFactory(item=user)
        response = embedding.get_summary_chat_prompt()
        assert all(isinstance(x, str) for x in response)

    def test_hashcode_consistency(self):
        user = UserFactory(
            job=faker.sentence(),
            professional_description=faker.text(),
            personal_description=faker.text(),
        )
        embedding = UserEmbeddingFactory(item=user)
        SkillFactory.create_batch(3, user=user, level=3)
        SkillFactory.create_batch(3, user=user, level=4)
        prompt_hashcode = embedding.hash_prompt()
        for _ in range(10):
            assert embedding.hash_prompt() == prompt_hashcode
