import datetime

from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
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
        cls.data = {
            "none": {
                "groups": [],
                "visible_by_all": False,
            },
            "all": {
                "groups": [],
                "visible_by_all": True,
            },
            "public": {
                "groups": [
                    PeopleGroupFactory(
                        organization=cls.organization,
                        publication_status=PeopleGroup.PublicationStatus.PUBLIC,
                    )
                ],
                "visible_by_all": False,
            },
            "private": {
                "groups": [
                    PeopleGroupFactory(
                        organization=cls.organization,
                        publication_status=PeopleGroup.PublicationStatus.PRIVATE,
                    )
                ],
                "visible_by_all": False,
            },
            "org": {
                "groups": [
                    PeopleGroupFactory(
                        organization=cls.organization,
                        publication_status=PeopleGroup.PublicationStatus.ORG,
                    )
                ],
                "visible_by_all": False,
            },
        }
        cls.events = {
            key: EventFactory(
                organization=cls.organization,
                people_groups=value["groups"],
                visible_by_all=value["visible_by_all"],
            )
            for key, value in cls.data.items()
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("all",)),
            (TestRoles.DEFAULT, ("all",)),
            (TestRoles.SUPERADMIN, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_USER, ("none", "all")),
            (TestRoles.ORG_VIEWER, ("public", "org")),
            (TestRoles.GROUP_LEADER, ("all", "private")),
            (TestRoles.GROUP_MANAGER, ("all", "private")),
            (TestRoles.GROUP_MEMBER, ("all", "private")),
        ]
    )
    def test_list_event(self, role, expected_count):
        user = self.get_parameterized_test_user(
            role, instances=self.data["private"]["groups"]
        )
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


class FilterOrderEventTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = UserFactory(groups=[get_superadmins_group()])
        cls.date_1 = make_aware(datetime.datetime(2020, 1, 1))
        cls.date_2 = make_aware(datetime.datetime(2021, 1, 1))
        cls.date_3 = make_aware(datetime.datetime(2022, 1, 1))
        cls.event_1 = EventFactory(organization=cls.organization, event_date=cls.date_1)
        cls.event_2 = EventFactory(organization=cls.organization, event_date=cls.date_2)
        cls.event_3 = EventFactory(organization=cls.organization, event_date=cls.date_3)

    def test_filter_from_date(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Event-list", args=(self.organization.code,))
            + f"?from_date={self.date_2.date()}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {event["id"] for event in content},
            {self.event_2.id, self.event_3.id},
        )

    def test_filter_to_date(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Event-list", args=(self.organization.code,))
            + f"?to_date={self.date_2.date()}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {event["id"] for event in content},
            {self.event_1.id, self.event_2.id},
        )

    def test_order_by_event_date(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Event-list", args=(self.organization.code,))
            + "?ordering=event_date"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertListEqual(
            [event["id"] for event in content],
            [self.event_1.id, self.event_2.id, self.event_3.id],
        )

    def test_order_by_event_date_reverse(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Event-list", args=(self.organization.code,))
            + "?ordering=-event_date"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertListEqual(
            [event["id"] for event in content],
            [self.event_3.id, self.event_2.id, self.event_1.id],
        )
