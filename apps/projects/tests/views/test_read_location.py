from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import (
    PeopleGroupFactory,
    PeopleGroupLocationFactory,
)
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

        cls.public_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organization=cls.organization,
            location=PeopleGroupLocationFactory(),
        )
        cls.org_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.ORG,
            organization=cls.organization,
            location=PeopleGroupLocationFactory(),
        )
        cls.private_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organization=cls.organization,
            location=PeopleGroupLocationFactory(),
        )
        cls.child_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organization=cls.organization,
            location=PeopleGroupLocationFactory(),
        )

        cls.groups = {
            "public": cls.public_group,
            "org": cls.org_group,
            "private": cls.private_group,
            "child": cls.child_group,
        }

        cls.locations_group = {
            "public": cls.public_group.location,
            "org": cls.org_group.location,
            "private": cls.private_group.location,
            "child": cls.child_group.location,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", "child")),
            (TestRoles.DEFAULT, ("public", "child")),
            (TestRoles.SUPERADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private", "child")),
            (TestRoles.ORG_USER, ("public", "org", "child")),
            (TestRoles.ORG_VIEWER, ("public", "org", "child")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private", "child")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private", "child")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private", "child")),
        ]
    )
    def test_list_project_location(self, role, retrieved_locations):
        user = self.get_parameterized_test_user(
            role, instances=[*self.projects.values()]
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("General-location-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()

        # projects
        self.assertEqual(len(content["projects"]), len(retrieved_locations))
        self.assertSetEqual(
            {a["id"] for a in content["projects"]},
            {a.id for a in [self.locations[a] for a in retrieved_locations]},
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", "child")),
            (TestRoles.DEFAULT, ("public", "child")),
            (TestRoles.SUPERADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private", "child")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private", "child")),
            (TestRoles.ORG_USER, ("public", "org", "child")),
            (TestRoles.ORG_VIEWER, ("public", "org", "child")),
            (TestRoles.GROUP_MEMBER, ("public", "org", "private", "child")),
            (TestRoles.GROUP_LEADER, ("public", "org", "private", "child")),
            (TestRoles.GROUP_MANAGER, ("public", "org", "private", "child")),
        ]
    )
    def test_list_group_location(self, role, retrieved_locations):
        user = self.get_parameterized_test_user(role, instances=[*self.groups.values()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("General-location-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()

        self.assertEqual(len(content["groups"]), len(retrieved_locations))
        self.assertSetEqual(
            {a["id"] for a in content["groups"]},
            {a.id for a in [self.locations_group[a] for a in retrieved_locations]},
        )
