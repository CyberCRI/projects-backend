from unittest.mock import patch

from faker import Faker

from apps.commons.test import JwtAPITestCase
from apps.misc.factories import WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import BlogEntryFactory, ProjectFactory
from services.mistral.factories import ProjectEmbeddingFactory
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class ProjectEmbeddingVisibilityTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    def test_set_visibility_with_description(self):
        project = ProjectFactory(
            description=faker.text(), organizations=[self.organization]
        )
        embedding = ProjectEmbeddingFactory(item=project)
        embedding.set_visibility()
        assert embedding.is_visible

    def test_set_visibility_with_blog_entries(self):
        project = ProjectFactory(description="", organizations=[self.organization])
        BlogEntryFactory(project=project)
        embedding = ProjectEmbeddingFactory(item=project)
        embedding.set_visibility()
        assert embedding.is_visible

    def test_set_visibility_not_visible(self):
        project = ProjectFactory(description="", organizations=[self.organization])
        embedding = ProjectEmbeddingFactory(item=project)
        embedding.set_visibility()
        assert not embedding.is_visible


class VectorizeProjectTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_description(self, mocked_embeddings, mocked_chat):
        project = ProjectFactory(
            description=faker.text(), organizations=[self.organization]
        )
        embedding = ProjectEmbeddingFactory(item=project)
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
    def test_vectorize_with_blog_entries(self, mocked_embeddings, mocked_chat):
        project = ProjectFactory(description="", organizations=[self.organization])
        embedding = ProjectEmbeddingFactory(item=project)
        BlogEntryFactory(project=project)
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
        project = ProjectFactory(description="", organizations=[self.organization])
        embedding = ProjectEmbeddingFactory(item=project)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        vector = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(vector)
        embedding.vectorize()
        assert not embedding.is_visible
        assert embedding.embedding is None
        assert embedding.prompt_hashcode == ""


class ProjectEmbeddingMiscTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    def test_get_summary_chat_system(self):
        project = ProjectFactory(
            description=faker.text(), organizations=[self.organization]
        )
        embedding = ProjectEmbeddingFactory(item=project)
        response = embedding.get_summary_chat_system()
        assert all(isinstance(x, str) for x in response)

    def test_get_summary_chat_prompt(self):
        project = ProjectFactory(
            description=faker.text(), organizations=[self.organization]
        )
        embedding = ProjectEmbeddingFactory(item=project)
        BlogEntryFactory.create_batch(3, project=project)
        project.wikipedia_tags.add(*WikipediaTagFactory.create_batch(3))
        response = embedding.get_summary_chat_prompt()
        assert all(isinstance(x, str) for x in response)

    def test_hashcode_consistency(self):
        project = ProjectFactory(
            description=faker.text(), organizations=[self.organization]
        )
        embedding = ProjectEmbeddingFactory(item=project)
        BlogEntryFactory.create_batch(3, project=project)
        project.wikipedia_tags.add(*WikipediaTagFactory.create_batch(3))
        prompt_hashcode = embedding.hash_prompt()
        for _ in range(10):
            assert embedding.hash_prompt() == prompt_hashcode
