from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.newsfeed.factories import NewsFactory
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateNewsImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
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
    def test_create_news_image(self, role, expected_code):
        organization = self.organization
        news = NewsFactory(
            organization=self.organization, people_groups=[self.people_group]
        )
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {"file": self.get_test_image_file()}
        response = self.client.post(
            reverse(
                "News-images-list",
                args=(organization.code, news.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertIsNotNone(content["static_url"])
            self.assertEqual(
                content["static_url"] + "/",
                reverse(
                    "News-images-detail",
                    args=(organization.code, news.id, content["id"]),
                ),
            )


class UpdateNewsImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.image = cls.get_test_image()
        cls.news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.people_group],
        )
        cls.news.images.add(cls.image)

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
    def test_update_news_image(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
            "scale_y": faker.pyfloat(min_value=1.0, max_value=2.0),
            "left": faker.pyfloat(min_value=1.0, max_value=2.0),
            "top": faker.pyfloat(min_value=1.0, max_value=2.0),
            "natural_ratio": faker.pyfloat(min_value=1.0, max_value=2.0),
        }
        response = self.client.patch(
            reverse(
                "News-images-detail",
                args=(self.organization.code, self.news.id, self.image.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.json()["scale_x"], payload["scale_x"])
            self.assertEqual(response.json()["scale_y"], payload["scale_y"])
            self.assertEqual(response.json()["left"], payload["left"])
            self.assertEqual(response.json()["top"], payload["top"])
            self.assertEqual(response.json()["natural_ratio"], payload["natural_ratio"])


class DeleteNewsImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.people_group],
        )

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
    def test_delete_news_image(self, role, expected_code):
        image = self.get_test_image()
        self.news.images.add(image)
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "News-images-detail",
                args=(self.organization.code, self.news.id, image.id),
            ),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.news.refresh_from_db()
            self.assertFalse(self.news.images.filter(id=image.id).exists())


class RetrieveNewsImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        cls.private_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
        )
        cls.org_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )

        cls.none_news = NewsFactory(organization=cls.organization, visible_by_all=False)
        cls.none_image = cls.get_test_image()
        cls.none_news.images.add(cls.none_image)

        cls.all_news = NewsFactory(organization=cls.organization, visible_by_all=True)
        cls.all_image = cls.get_test_image()
        cls.all_news.images.add(cls.all_image)

        cls.public_news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.public_people_group],
            visible_by_all=False,
        )
        cls.public_image = cls.get_test_image()
        cls.public_news.images.add(cls.public_image)

        cls.private_news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.private_people_group],
            visible_by_all=False,
        )
        cls.private_image = cls.get_test_image()
        cls.private_news.images.add(cls.private_image)

        cls.org_news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.org_people_group],
            visible_by_all=False,
        )
        cls.org_image = cls.get_test_image()
        cls.org_news.images.add(cls.org_image)

        cls.news = {
            "none": {
                "news": cls.none_news,
                "image": cls.none_image,
            },
            "all": {
                "news": cls.all_news,
                "image": cls.all_image,
            },
            "public": {
                "news": cls.public_news,
                "image": cls.public_image,
            },
            "private": {
                "news": cls.private_news,
                "image": cls.private_image,
            },
            "org": {
                "news": cls.org_news,
                "image": cls.org_image,
            },
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("all", "public")),
            (TestRoles.DEFAULT, ("all", "public")),
            (TestRoles.SUPERADMIN, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("none", "all", "public", "private", "org")),
            (TestRoles.ORG_USER, ("none", "all", "public", "org")),
            (TestRoles.GROUP_LEADER, ("all", "public", "private")),
            (TestRoles.GROUP_MANAGER, ("all", "public", "private")),
            (TestRoles.GROUP_MEMBER, ("all", "public", "private")),
        ]
    )
    def test_retrieve_news_images(self, role, retrieved_news):
        user = self.get_parameterized_test_user(
            role, instances=[self.private_people_group]
        )
        self.client.force_authenticate(user)
        for key, value in self.news.items():
            news_id = value["news"].id
            image_id = value["image"].id
            response = self.client.get(
                reverse(
                    "News-images-detail",
                    args=(self.organization.code, news_id, image_id),
                )
            )
            if key in retrieved_news:
                self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
