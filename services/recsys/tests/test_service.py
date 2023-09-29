from unittest.mock import patch

from django.test import TestCase

from apps.misc.factories import WikipediaTagFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from services.recsys.tests.mocks import RecsysMockResponse

from ..interface import RecsysService


class CommandsTestCase(TestCase):
    def test_get_text_query_from_project(self):
        project = ProjectFactory(language="fr", description="<p>description</p>")
        wikipedia_tags = WikipediaTagFactory.create_batch(5)
        project.wikipedia_tags.add(*wikipedia_tags)
        query = RecsysService.get_text_query_from_project(project)
        assert project.title in query
        assert "<p>description</p>" not in query
        assert "description" in query
        assert all(tag.name_fr in query for tag in wikipedia_tags)

        project.language = "en"
        project.save()
        query = RecsysService.get_text_query_from_project(project)
        assert project.title in query
        assert "<p>description</p>" not in query
        assert "description" in query
        assert all(tag.name_en in query for tag in wikipedia_tags)

    @patch(target="requests.post")
    def test_get_similar_projects(self, mocked):
        projects = ProjectFactory.create_batch(
            5, publication_status=Project.PublicationStatus.PUBLIC
        )
        mock_response = RecsysMockResponse(projects)
        mocked.side_effect = lambda url, data: mock_response
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        results = RecsysService.get_similar_projects(project, 5, ["en", "fr"])
        assert set(results.keys()) == {project.id for project in projects}
        assert all(isinstance(similarity, float) for similarity in results.values())
        assert all(0.0 <= similarity <= 10.0 for similarity in results.values())
