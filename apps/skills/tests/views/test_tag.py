from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import TagFactory
from apps.skills.models import Tag

faker = Faker()


class RetrieveTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization_1 = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        cls.tag_1 = TagFactory(organization=cls.organization_1)
        cls.tag_2 = TagFactory(organization=cls.organization_2)
        cls.esco_tag = TagFactory(type=Tag.TagType.ESCO)
        cls.wikipedia_tag = TagFactory(type=Tag.TagType.WIKIPEDIA)
        cls.other_tags = TagFactory.create_batch(2)
        cls.filtered_tags = [cls.tag_1, cls.tag_2, cls.esco_tag, cls.wikipedia_tag]
        cls.tags = [*cls.filtered_tags, *cls.other_tags]

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_tags(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ReadTag-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.tags))
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {tag.id for tag in self.tags},
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_filter_tags_by_ids(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ReadTag-list")
            + f"?ids={','.join([str(tag.id) for tag in self.filtered_tags])}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.filtered_tags))
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {tag.id for tag in self.filtered_tags},
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_retrieve_tag(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        for tag in self.tags:
            response = self.client.get(reverse("ReadTag-detail", args=(tag.id,)))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()
            self.assertEqual(content["title_fr"], tag.title_fr)
            self.assertEqual(content["title_en"], tag.title_en)
            self.assertEqual(content["title"], tag.title_en)
            self.assertEqual(content["description_fr"], tag.description_fr)
            self.assertEqual(content["description_en"], tag.description_en)
            self.assertEqual(content["description"], tag.description_en)
