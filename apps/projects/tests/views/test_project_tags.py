from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test.testcases import TagTestCase
from apps.misc.factories import WikipediaTagFactory
from apps.misc.models import WikipediaTag
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects import factories
from apps.projects.tests.views.test_project import ProjectJwtAPITestCase


class ProjectTagsTestCase(ProjectJwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectFactory.build(header_image=self.test_image)
        org = OrganizationFactory()
        pc = ProjectCategoryFactory(background_image=self.test_image, organization=org)
        qids = ["Q1735684", "Q12335103", "Q3737270"]
        WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        images = [i.pk for i in [self.get_test_image() for _ in range(2)]]

        payload = {
            "title": fake.title,
            "description": fake.description,
            "header_image_id": fake.header_image.pk,
            "is_locked": fake.is_locked,
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": [org.code],
            "wikipedia_tags_ids": qids,
            "images_ids": images,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        content = response.json()
        wikipedia_tags = content["wikipedia_tags"]
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
        org = OrganizationFactory()
        qids = ["Q560361", "Q12335103", "Q3737270"]
        to_update = WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        pc = ProjectCategoryFactory(organization=org)
        project = factories.ProjectFactory(categories=[pc], organizations=[org])
        project.wikipedia_tags.add(to_update)

        payload = {
            "title": "NewTitle",
            "description": project.description,
            "is_shareable": project.is_shareable,
            "purpose": project.purpose,
            "language": project.language,
            "publication_status": project.publication_status,
            "life_status": project.life_status,
            "sdgs": project.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": [org.code],
            "wikipedia_tags_ids": qids,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Project-detail", args=(project.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        wikipedia_tags = content["wikipedia_tags"]
        self.assertEqual(len(wikipedia_tags), 3)

        updated = WikipediaTag.objects.filter(wikipedia_qid=qids[0])
        self.assertEqual(updated.count(), 1)
        self.assertEqual(updated.first().name, "draft document")
        self.assertEqual(updated.first().name_fr, "brouillon")
        self.assertEqual(updated.first().name_en, "draft document")

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_partial_update(self, mocked):
        mocked.side_effect = self.side_effect
        qids = ["Q1735684", "Q12335103", "Q3737270"]
        to_update = WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        org = OrganizationFactory()
        pc = ProjectCategoryFactory(organization=org)
        project = factories.ProjectFactory(categories=[pc], organizations=[org])
        project.wikipedia_tags.add(to_update)

        payload = {
            "wikipedia_tags_ids": qids,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Project-detail", args=(project.pk,)), data=payload
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
