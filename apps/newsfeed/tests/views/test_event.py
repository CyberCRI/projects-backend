import datetime

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.newsfeed.factories import EventFactory
from apps.newsfeed.models import Event
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateEventTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_event(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "organization": self.organization.code,
            "title": faker.sentence(),
            "content": faker.text(),
            "event_date": datetime.date.today().isoformat(),
            "people_groups": [self.people_group.id],
        }

        response = self.client.post(
            reverse("Event-list", args=(organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["content"], payload["content"])
            self.assertEqual(content["people_groups"], payload["people_groups"])


class UpdateEventTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.event = EventFactory(
            organization=cls.organization, people_groups=[cls.people_group]
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_event(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "event_date": datetime.date.today().isoformat(),
        }
        response = self.client.patch(
            reverse(
                "Event-detail",
                args=(
                    self.organization.code,
                    self.event.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["content"], payload["content"])


class DeleteEventTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_event(self, role, expected_code):
        event = EventFactory(
            organization=self.organization, people_groups=[self.people_group]
        )
        event_id = event.id
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Event-detail",
                args=(
                    self.organization.code,
                    event.id,
                ),
            )
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Event.objects.filter(id=event_id).exists())


class RetrieveEventTestCase(JwtAPITestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_groups = {
            "none": [],
            "public": [PeopleGroupFactory(organization=cls.organization, publication_status=PeopleGroup.PublicationStatus.PUBLIC)],
            "private": [PeopleGroupFactory(organization=cls.organization, publication_status=PeopleGroup.PublicationStatus.PRIVATE)],
            "org": [PeopleGroupFactory(organization=cls.organization, publication_status=PeopleGroup.PublicationStatus.ORG)],
        }
        cls.events = {
            key: EventFactory(organization=cls.organization, people_groups=value)
            for key, value in cls.people_groups.items()
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("none", "public")),
            (TestRoles.DEFAULT, ("none", "public")),
            (TestRoles.SUPERADMIN, ("none", "public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("none", "public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("none", "public", "private", "org")),
            (TestRoles.ORG_USER, ("none", "public", "org")),
            (TestRoles.GROUP_LEADER, ("none", "public", "private")),
            (TestRoles.GROUP_MANAGER, ("none", "public", "private")),
            (TestRoles.GROUP_MEMBER, ("none", "public", "private")),
        ]
    )
    def test_list_event(self, role, expected_count):
        user = self.get_parameterized_test_user(role, instances=self.people_groups["private"])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Event-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {event["id"] for event in content},
            {self.events[key].id for key in expected_count},
        )


class ValidateEventTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.other_organization = OrganizationFactory()
        cls.other_org_people_group = PeopleGroupFactory(
            organization=cls.other_organization
        )

    def setUp(self):
        super().setUp()

    def test_create_event_with_people_group_in_other_organization(self):
        user = self.get_parameterized_test_user(TestRoles.SUPERADMIN, instances=[])
        self.client.force_authenticate(user=user)
        payload = {
            "organization": self.organization.code,
            "title": faker.sentence(),
            "content": faker.text(),
            "event_date": datetime.date.today().isoformat(),
            "people_groups": [self.other_org_people_group.id],
        }
        response = self.client.post(
            reverse("Event-list", args=(self.organization.code,)), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "people_groups": [
                    "The people groups of an event must belong to the same organization"
                ]
            },
        )

    def test_update_event_with_people_group_in_other_organization(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        event = EventFactory(
            organization=self.organization, people_groups=[people_group]
        )
        user = self.get_parameterized_test_user(TestRoles.SUPERADMIN, instances=[])
        self.client.force_authenticate(user=user)
        payload = {
            "people_groups": [self.other_org_people_group.id],
        }
        response = self.client.patch(
            reverse(
                "Event-detail",
                args=(
                    self.organization.code,
                    event.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "people_groups": [
                    "The people groups of an event must belong to the same organization"
                ]
            },
        )
