from unittest.mock import patch

from faker import Faker

from apps.commons.test import JwtAPITestCase
from apps.projects.factories import BlogEntryFactory, ProjectFactory
from services.mistral.tasks import queue_or_create_project_embedding_task
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class ProjectEmbeddingVisibilityTestCase(JwtAPITestCase):
    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    def test_set_visibility_with_description(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description=faker.text())
        project.embedding.set_visibility()
        assert project.embedding.is_visible

    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    def test_set_visibility_with_blog_entries(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description="")
        BlogEntryFactory(project=project)
        project.embedding.set_visibility()
        assert project.embedding.is_visible

    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    def test_set_visibility_not_visible(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description="")
        project.embedding.set_visibility()
        assert not project.embedding.is_visible


class ProjectEmbeddingTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    def test_get_summary_chat_system(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description=faker.text())
        response = project.embedding.get_summary_chat_system()
        assert all(isinstance(x, str) for x in response)

    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    def test_get_summary_chat_prompt(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description=faker.text())
        response = project.embedding.get_summary_chat_prompt()
        assert all(isinstance(x, str) for x in response)

    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    def test_queue_or_create_new_project(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory()
        project.refresh_from_db()
        assert project.embedding.queued_for_update is True

    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    def test_queue_or_create_existing_project(self, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description=faker.text())
        project.embedding.queued_for_update = False
        project.embedding.save()
        project.description = faker.text()
        project.save()
        project.refresh_from_db()
        assert project.embedding.queued_for_update is True


class ProjectVectorizeTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_description(
        self, mocked_embeddings, mocked_chat, mocked_delay
    ):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description=faker.text())
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            embedding
        )
        project.embedding.vectorize()
        assert project.embedding.is_visible
        assert project.embedding.embedding == embedding
        assert project.embedding.prompt_hashcode != ""

    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_with_blog_entries(
        self, mocked_embeddings, mocked_chat, mocked_delay
    ):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description="")
        BlogEntryFactory(project=project)
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            embedding
        )
        project.embedding.vectorize()
        assert project.embedding.is_visible
        assert project.embedding.embedding == embedding
        assert project.embedding.prompt_hashcode != ""

    @patch("services.mistral.signals.queue_or_create_project_embedding_task.delay")
    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_vectorize_not_visible(self, mocked_embeddings, mocked_chat, mocked_delay):
        mocked_delay.side_effect = queue_or_create_project_embedding_task
        project = ProjectFactory(description="")
        messages = [faker.sentence(nb_words=6) for _ in range(3)]
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked_chat.return_value = self.chat_response_mocked_return(messages)
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            embedding
        )
        project.embedding.vectorize()
        assert not project.embedding.is_visible
        assert project.embedding.embedding is None
        assert project.embedding.prompt_hashcode == ""
