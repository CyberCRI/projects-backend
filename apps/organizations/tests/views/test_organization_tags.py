from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase
from apps.misc.factories import WikipediaTagFactory
from apps.misc.models import WikipediaTag
from apps.organizations import factories


class OrganisationTagsTestCase(JwtAPITestCase, TagTestCase):
    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.OrganizationFactory.build()
        parent = factories.OrganizationFactory()
        qids = ["Q1735684", "Q12335103", "Q3737270"]
        WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        payload = {
            "background_color": fake.background_color,
            "code": fake.code,
            "contact_email": fake.contact_email,
            "dashboard_title": fake.dashboard_title,
            "dashboard_subtitle": fake.dashboard_subtitle,
            "language": fake.language,
            "logo_image_id": fake.logo_image.pk,
            "is_logo_visible_on_parent_dashboard": fake.is_logo_visible_on_parent_dashboard,
            "name": fake.name,
            "website_url": fake.website_url,
            "created_at": fake.created_at,
            "updated_at": fake.updated_at,
            "wikipedia_tags_ids": qids,
            "parent_id": parent.id,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Organization-list"), data=payload)
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
        orga = factories.OrganizationFactory()
        orga.wikipedia_tags.add(to_update)
        parent = factories.OrganizationFactory()
        payload = {
            "background_color": orga.background_color,
            "code": "NewCode",
            "contact_email": orga.contact_email,
            "dashboard_title": orga.dashboard_title,
            "dashboard_subtitle": orga.dashboard_subtitle,
            "language": orga.language,
            "logo_image_id": orga.logo_image.pk,
            "is_logo_visible_on_parent_dashboard": orga.is_logo_visible_on_parent_dashboard,
            "name": orga.name,
            "website_url": orga.website_url,
            "created_at": orga.created_at,
            "updated_at": orga.updated_at,
            "wikipedia_tags_ids": qids,
            "parent_id": parent.id,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Organization-detail", args=(orga.code,)), data=payload
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

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_partial_update(self, mocked):
        mocked.side_effect = self.side_effect
        qids = ["Q1735684", "Q12335103", "Q3737270"]
        to_update = WikipediaTagFactory(name="to update", wikipedia_qid=qids[0])
        orga = factories.OrganizationFactory()
        orga.wikipedia_tags.add(to_update)

        payload = {
            "wikipedia_tags_ids": qids,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", args=(orga.code,)), data=payload
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
