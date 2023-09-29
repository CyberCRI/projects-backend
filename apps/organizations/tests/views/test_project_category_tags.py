from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase
from apps.misc.factories import TagFactory, WikipediaTagFactory
from apps.misc.models import WikipediaTag
from apps.organizations import factories


class ProjectCategoryTagsTestCase(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory.build(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        qids = ["Q1735684", "Q12335103", "Q3737270"]
        WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        payload = {
            "background_color": fake.background_color,
            "background_image_id": fake.background_image.pk,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "wikipedia_tags_ids": qids,
            "organization_code": organization.code,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        content = response.json()
        wikipedia_tags = content["wikipedia_tags"]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, content)
        self.assertEqual(len(wikipedia_tags), 3)
        self.assertEqual(
            sorted(qids), sorted([t["wikipedia_qid"] for t in wikipedia_tags])
        )

        updated = WikipediaTag.objects.filter(wikipedia_qid=qids[0])
        self.assertEqual(updated.count(), 1)
        self.assertEqual(updated.first().name_fr, "Kate Foo Kune fr")
        self.assertEqual(updated.first().name_en, "Kate Foo Kune en")

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update(self, mocked):
        mocked.side_effect = self.side_effect
        qids = ["Q1735684", "Q12335103", "Q3737270"]
        to_update = WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        pc.wikipedia_tags.add(to_update)
        payload = {
            "background_color": pc.background_color,
            "background_image_id": pc.background_image.id,
            "description": pc.description,
            "foreground_color": pc.foreground_color,
            "is_reviewable": pc.is_reviewable,
            "name": "New name",
            "order_index": pc.order_index,
            "wikipedia_tags_ids": qids,
            "organization_tags_ids": [TagFactory().id],
            "organization_code": pc.organization.code,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK, content)
        self.assertEqual(len(response.data["organization_tags"]), 1)
        self.assertEqual(len(response.data["wikipedia_tags"]), 3)

        updated = WikipediaTag.objects.filter(wikipedia_qid=qids[0])
        self.assertEqual(updated.count(), 1)
        self.assertEqual(updated.first().name_fr, "Kate Foo Kune fr")
        self.assertEqual(updated.first().name_en, "Kate Foo Kune en")

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_partial_update(self, mocked):
        mocked.side_effect = self.side_effect
        qids = ["Q1735684", "Q12335103", "Q3737270"]
        to_update = WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        pc.wikipedia_tags.add(to_update)
        payload = {
            "wikipedia_tags_ids": qids,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        wikipedia_tags = content["wikipedia_tags"]

        self.assertEqual(response.status_code, status.HTTP_200_OK, content)
        self.assertEqual(len(wikipedia_tags), 3)

        updated = WikipediaTag.objects.filter(wikipedia_qid=qids[0])
        self.assertEqual(updated.count(), 1)
        self.assertEqual(updated.first().name_fr, "Kate Foo Kune fr")
        self.assertEqual(updated.first().name_en, "Kate Foo Kune en")
