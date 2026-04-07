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
        cls.organization_other = OrganizationFactory()
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

        cls.projects_other_orga = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization_other],
        )

        cls.public_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organization=cls.organization,
        )
        cls.org_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.ORG,
            organization=cls.organization,
        )
        cls.private_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organization=cls.organization,
        )
        cls.child_group = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organization=cls.child_organization,
        )

        cls.groups = {
            "public": cls.public_group,
            "org": cls.org_group,
            "private": cls.private_group,
            "child": cls.child_group,
        }
        cls.group_other_orga = PeopleGroupFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organization=cls.organization_other,
        )

        cls.locations_group = {
            "public": PeopleGroupLocationFactory(people_group=cls.public_group),
            "org": PeopleGroupLocationFactory(people_group=cls.org_group),
            "private": PeopleGroupLocationFactory(people_group=cls.private_group),
            "child": PeopleGroupLocationFactory(people_group=cls.child_group),
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
            reverse("General-location-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        locations = response.json()

        # projects (from organization, not organization_other)
        self.assertSetEqual(
            {
                location["content_id"]
                for location in locations
                if location["content_type"] == "project"
            },
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
            reverse("General-location-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        locations = response.json()

        # projects (from organization, not organization_other)
        self.assertSetEqual(
            {
                location["content_id"]
                for location in locations
                if location["content_type"] == "people_group"
            },
            {a.id for a in [self.locations[a] for a in retrieved_locations]},
        )
