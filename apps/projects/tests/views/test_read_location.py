from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import LocationFactory, ProjectFactory
from apps.projects.models import Project


class ReadLocationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.child_organization = OrganizationFactory(parent=cls.organization)
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.child_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.child_organization],
        )
        cls.projects = {
            "public": cls.public_project,
            "org": cls.org_project,
            "private": cls.private_project,
            "child": cls.child_project,
        }
        cls.locations = {
            "public": LocationFactory(project=cls.public_project),
            "org": LocationFactory(project=cls.org_project),
            "private": LocationFactory(project=cls.private_project),
            "child": LocationFactory(project=cls.child_project),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", "child")),
            (TestRoles.DEFAULT, ("public", "child")),
            (TestRoles.SUPERADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private", "child")),
            (TestRoles.ORG_USER, ("public", "org", "child")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private", "child")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private", "child")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private", "child")),
        ]
    )
    def test_retrieve_location(self, role, retrieved_locations):
        for publication_status, location in self.locations.items():
            project = location.project
            user = self.get_parameterized_test_user(role, instances=[project])
            self.client.force_authenticate(user)
            response = self.client.get(
                reverse("Read-location-detail", args=(location.id,)),
            )
            if publication_status in retrieved_locations:
                assert response.status_code == status.HTTP_200_OK
                content = response.json()
                assert content["id"] == location.id
            else:
                assert response.status_code == status.HTTP_404_NOT_FOUND

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", "child")),
            (TestRoles.DEFAULT, ("public", "child")),
            (TestRoles.SUPERADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private", "child")),
            (TestRoles.ORG_USER, ("public", "org", "child")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private", "child")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private", "child")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private", "child")),
        ]
    )
    def test_list_location(self, role, retrieved_locations):
        user = self.get_parameterized_test_user(
            role, instances=[*self.projects.values()]
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Read-location-list"),
        )
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert len(content) == len(retrieved_locations)
        assert {a["id"] for a in content} == {
            a.id for a in [self.locations[a] for a in retrieved_locations]
        }
