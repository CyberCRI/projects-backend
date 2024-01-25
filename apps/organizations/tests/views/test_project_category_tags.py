import random
from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCaseMixin
from apps.misc.factories import WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory

faker = Faker()


class ProjectCategoryTagsTestCase(JwtAPITestCase, TagTestCaseMixin):
    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        wikipedia_qid_1 = self.get_random_wikipedia_qid()
        wikipedia_qid_2 = self.get_random_wikipedia_qid()
        wikipedia_qid_3 = self.get_random_wikipedia_qid()
        to_update = WikipediaTagFactory(wikipedia_qid=wikipedia_qid_1)
        organization = OrganizationFactory()
        payload = {
            "description": faker.text(),
            "name": faker.word(),
            "wikipedia_tags_ids": [wikipedia_qid_1, wikipedia_qid_2, wikipedia_qid_3],
            "organization_code": organization.code,
        }
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.post(reverse("Category-list"), data=payload)
        assert response.status_code == status.HTTP_201_CREATED
        content = response.json()
        wikipedia_tags = content["wikipedia_tags"]
        assert len(wikipedia_tags) == 3
        assert {t["wikipedia_qid"] for t in wikipedia_tags} == {
            wikipedia_qid_1,
            wikipedia_qid_2,
            wikipedia_qid_3,
        }
        to_update.refresh_from_db()
        assert to_update.name == f"name_en_{wikipedia_qid_1}"
        assert to_update.name_fr == f"name_fr_{wikipedia_qid_1}"
        assert to_update.name_en == f"name_en_{wikipedia_qid_1}"

    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update(self, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        wikipedia_qid_1 = self.get_random_wikipedia_qid()
        wikipedia_qid_2 = self.get_random_wikipedia_qid()
        wikipedia_qid_3 = self.get_random_wikipedia_qid()
        category = ProjectCategoryFactory()
        to_update = WikipediaTagFactory(wikipedia_qid=wikipedia_qid_1)
        payload = {
            "wikipedia_tags_ids": [wikipedia_qid_1, wikipedia_qid_2, wikipedia_qid_3],
        }
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.patch(
            reverse("Category-detail", args=(category.pk,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        wikipedia_tags = content["wikipedia_tags"]
        assert len(wikipedia_tags) == 3
        assert {t["wikipedia_qid"] for t in wikipedia_tags} == {
            wikipedia_qid_1,
            wikipedia_qid_2,
            wikipedia_qid_3,
        }
        to_update.refresh_from_db()
        assert to_update.name == f"name_en_{wikipedia_qid_1}"
        assert to_update.name_fr == f"name_fr_{wikipedia_qid_1}"
        assert to_update.name_en == f"name_en_{wikipedia_qid_1}"
