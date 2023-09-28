from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase
from apps.misc.factories import WikipediaTagFactory
from apps.misc.models import WikipediaTag
from apps.organizations import factories, models
from apps.organizations.models import ProjectCategory


class ProjectCategoryTestCaseAnonymous(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_anonymous(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory.build(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": fake.background_color,
            "background_image_id": fake.background_image.pk,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "wikipedia_tags_ids": wikipedia_tags,
            "organization_code": organization.code,
        }

        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_anonymous(self):
        obj = factories.ProjectCategoryFactory(background_image=self.test_image)
        response = self.client.get(reverse("Category-detail", args=(obj.pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_anonymous(self):
        factories.ProjectCategoryFactory.create_batch(
            2, background_image=self.test_image
        )
        response = self.client.get(reverse("Category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_destroy_anonymous(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        response = self.client.delete(reverse("Category-detail", args=(pc.pk,)))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_anonymous(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": fake.background_color,
            "background_image_id": fake.background_image.id,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "wikipedia_tags_ids": wikipedia_tags,
            "organization_code": organization.code,
        }
        response = self.client.put(
            reverse("Category-detail", args=(fake.id,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_anonymous(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        payload = {
            "name": "New name",
        }
        response = self.client.patch(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProjectCategoryTestCaseNoPermission(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_no_permission(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory.build(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": fake.background_color,
            "background_image_id": fake.background_image.pk,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "wikipedia_tags_ids": wikipedia_tags,
            "organization_code": organization.code,
        }

        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_no_permission(self):
        obj = factories.ProjectCategoryFactory(background_image=self.test_image)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Category-detail", args=(obj.pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_no_permission(self):
        factories.ProjectCategoryFactory.create_batch(
            2, background_image=self.test_image
        )
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_destroy_no_permission(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(reverse("Category-detail", args=(pc.pk,)))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_org_no_permission(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        user = UserFactory()
        pc.organization.users.add(user)
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Category-detail", args=(pc.pk,)))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_no_permission(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": fake.background_color,
            "background_image_id": fake.background_image.pk,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "wikipedia_tags_ids": wikipedia_tags,
            "organization_code": organization.code,
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.put(
            reverse("Category-detail", args=(fake.id,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_no_permission(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        payload = {
            "name": "New name",
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProjectCategoryTestCaseBasePermission(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_base_permission(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory.build(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": fake.background_color,
            "background_image_id": fake.background_image.pk,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "wikipedia_tags_ids": wikipedia_tags,
            "organization_code": organization.code,
        }

        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        content = response.json()
        self.assertIn("id", content)

        pc = models.ProjectCategory.objects.get(pk=content["id"])
        self.assertEqual(fake.background_color, pc.background_color)
        self.assertEqual(fake.background_image.pk, pc.background_image.pk)
        self.assertEqual(fake.foreground_color, pc.foreground_color)
        self.assertEqual(fake.is_reviewable, pc.is_reviewable)
        self.assertEqual(fake.name, pc.name)
        self.assertEqual(fake.order_index, pc.order_index)
        self.assertEqual(organization.pk, pc.organization.pk)
        self.assertEqual(
            wikipedia_tags,
            list(pc.wikipedia_tags.all().values_list("wikipedia_qid", flat=True)),
        )

    def test_retrieve_base_permission(self):
        obj = factories.ProjectCategoryFactory(background_image=self.test_image)
        wikipedia_tags = WikipediaTag.objects.bulk_create(
            WikipediaTagFactory.build_batch(3)
        )
        obj.wikipedia_tags.add(*wikipedia_tags)

        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Category-detail", args=(obj.pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(obj.background_color, content["background_color"])
        self.assertEqual(obj.background_image.pk, content["background_image"]["id"])
        self.assertEqual(obj.foreground_color, content["foreground_color"])
        self.assertEqual(obj.is_reviewable, content["is_reviewable"])
        self.assertEqual(obj.name, content["name"])
        self.assertEqual(obj.order_index, content["order_index"])
        self.assertEqual(obj.organization.code, content["organization"])
        self.assertEqual(
            {t.wikipedia_qid for t in wikipedia_tags},
            {t["wikipedia_qid"] for t in content["wikipedia_tags"]},
        )

    def test_list_base_permission(self):
        pcs = factories.ProjectCategoryFactory.create_batch(
            2, background_image=self.test_image
        )
        for pc in pcs:
            pc.wikipedia_tags.add(
                *WikipediaTag.objects.bulk_create(WikipediaTagFactory.build_batch(3))
            )

        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(content["count"], 2)

        results = [r for r in content["results"] if r["name"] == pcs[0].name][0]
        self.assertEqual(pcs[0].background_color, results["background_color"])
        self.assertEqual(pcs[0].background_image.pk, results["background_image"]["id"])
        self.assertEqual(pcs[0].foreground_color, results["foreground_color"])
        self.assertEqual(pcs[0].is_reviewable, results["is_reviewable"])
        self.assertEqual(pcs[0].name, results["name"])
        self.assertEqual(pcs[0].order_index, results["order_index"])
        self.assertEqual(pcs[0].organization.code, results["organization"])
        self.assertEqual(
            [t.wikipedia_qid for t in pcs[0].wikipedia_tags.all()],
            [t["wikipedia_qid"] for t in results["wikipedia_tags"]],
        )

        results = [r for r in content["results"] if r["name"] == pcs[1].name][0]
        self.assertEqual(pcs[1].background_color, results["background_color"])
        self.assertEqual(pcs[1].background_image.pk, results["background_image"]["id"])
        self.assertEqual(pcs[1].foreground_color, results["foreground_color"])
        self.assertEqual(pcs[1].is_reviewable, results["is_reviewable"])
        self.assertEqual(pcs[1].name, results["name"])
        self.assertEqual(pcs[1].order_index, results["order_index"])
        self.assertEqual(pcs[1].organization.code, results["organization"])
        self.assertEqual(
            [t.wikipedia_qid for t in pcs[1].wikipedia_tags.all()],
            [t["wikipedia_qid"] for t in results["wikipedia_tags"]],
        )

    def test_destroy_base_permission(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Category-detail", args=(pc.pk,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectCategory.objects.filter(pk=pc.pk).exists())

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_base_permission(self, mocked):
        mocked.side_effect = self.side_effect
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        payload = {
            "background_color": pc.background_color,
            "background_image_id": pc.background_image.id,
            "description": pc.description,
            "foreground_color": pc.foreground_color,
            "is_reviewable": pc.is_reviewable,
            "name": "New name",
            "order_index": pc.order_index,
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_code": pc.organization.code,
        }
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        pc.refresh_from_db()
        self.assertEqual(pc.name, "New name")

    def test_partial_update_base_permission(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        payload = {
            "name": "New name",
        }
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        pc.refresh_from_db()
        self.assertEqual(pc.name, "New name")


class ProjectCategoryTestCaseOrganizationPermission(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_org_permissions(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory.build(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        tags = ["Q1735684"]
        payload = {
            "background_color": fake.background_color,
            "background_image_id": fake.background_image.id,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_code": organization.code,
        }

        user = UserFactory(
            permissions=[("organizations.add_projectcategory", organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        content = response.json()
        self.assertIn("id", content)

        pc = models.ProjectCategory.objects.get(pk=content["id"])
        self.assertEqual(fake.background_color, pc.background_color)
        self.assertEqual(fake.background_image.pk, pc.background_image.pk)
        self.assertEqual(fake.foreground_color, pc.foreground_color)
        self.assertEqual(fake.is_reviewable, pc.is_reviewable)
        self.assertEqual(fake.name, pc.name)
        self.assertEqual(fake.order_index, pc.order_index)
        self.assertEqual(organization.pk, pc.organization.pk)
        self.assertEqual(
            tags, list(pc.wikipedia_tags.all().values_list("wikipedia_qid", flat=True))
        )

    def test_retrieve_org_permissions(self):
        obj = factories.ProjectCategoryFactory(background_image=self.test_image)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Category-detail", args=(obj.pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_org_permissions(self):
        factories.ProjectCategoryFactory.create_batch(
            2, background_image=self.test_image
        )
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_destroy_org_permissions(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        user = UserFactory(
            permissions=[("organizations.delete_projectcategory", pc.organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Category-detail", args=(pc.pk,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectCategory.objects.filter(pk=pc.pk).exists())

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_org_permissions(self, mocked):
        mocked.side_effect = self.side_effect
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        payload = {
            "background_color": pc.background_color,
            "background_image_id": pc.background_image.id,
            "description": pc.description,
            "foreground_color": pc.foreground_color,
            "is_reviewable": pc.is_reviewable,
            "name": "New name",
            "order_index": pc.order_index,
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_code": pc.organization.code,
        }
        user = UserFactory(
            permissions=[("organizations.change_projectcategory", pc.organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Category-detail", args=(pc.pk,)), data=payload, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        pc.refresh_from_db()
        self.assertEqual(pc.name, "New name")

    def test_partial_update_org_permissions(self):
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        payload = {
            "name": "New name",
        }
        user = UserFactory(
            permissions=[("organizations.change_projectcategory", pc.organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        pc.refresh_from_db()
        self.assertEqual(pc.name, "New name")


class ProjectCategoryTemplateTestCase(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_with_template(self, mocked):
        mocked.side_effect = self.side_effect
        fake = factories.ProjectCategoryFactory.build(background_image=self.test_image)
        organization = factories.OrganizationFactory()
        tags = ["Q1735684"]
        template = factories.TemplateFactory.build()
        payload = {
            "background_color": fake.background_color,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "tags_ids": tags,
            "organization_code": organization.code,
            "template": {
                "title_placeholder": template.title_placeholder,
                "description_placeholder": template.description_placeholder,
                "goal_placeholder": template.goal_placeholder,
                "blogentry_placeholder": template.blogentry_placeholder,
            },
        }
        user = UserFactory(
            permissions=[("organizations.add_projectcategory", organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        content = response.json()
        self.assertIn("id", content)
        self.assertIn("template", content)

        pc = models.ProjectCategory.objects.get(pk=content["id"])
        template = pc.template
        self.assertIsNotNone(template)
        self.assertEqual(
            template.title_placeholder, content["template"]["title_placeholder"]
        )
        self.assertEqual(
            template.description_placeholder,
            content["template"]["description_placeholder"],
        )
        self.assertEqual(
            template.goal_placeholder, content["template"]["goal_placeholder"]
        )
        self.assertEqual(
            template.blogentry_placeholder, content["template"]["blogentry_placeholder"]
        )

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_creating_missing_template(self, mocked):
        mocked.side_effect = self.side_effect
        pc = factories.ProjectCategoryFactory(background_image=self.test_image)
        template = factories.TemplateFactory.build()
        payload = {
            "background_color": pc.background_color,
            "description": pc.description,
            "foreground_color": pc.foreground_color,
            "is_reviewable": pc.is_reviewable,
            "name": "New name",
            "order_index": pc.order_index,
            "tags_ids": ["Q1735684"],
            "organization_code": pc.organization.code,
            "template": {
                "title_placeholder": template.title_placeholder,
                "description_placeholder": template.description_placeholder,
                "goal_placeholder": template.goal_placeholder,
                "blogentry_placeholder": template.blogentry_placeholder,
            },
        }
        user = UserFactory(
            permissions=[("organizations.change_projectcategory", pc.organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pc.refresh_from_db()
        template = pc.template
        self.assertIsNotNone(template)
        self.assertEqual(
            template.title_placeholder, payload["template"]["title_placeholder"]
        )
        self.assertEqual(
            template.description_placeholder,
            payload["template"]["description_placeholder"],
        )
        self.assertEqual(
            template.goal_placeholder, payload["template"]["goal_placeholder"]
        )
        self.assertEqual(
            template.blogentry_placeholder, payload["template"]["blogentry_placeholder"]
        )

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_updating_existing_template(self, mocked):
        mocked.side_effect = self.side_effect
        template = factories.TemplateFactory()
        pc = factories.ProjectCategoryFactory(template=template)
        payload = {
            "background_color": pc.background_color,
            "description": pc.description,
            "foreground_color": pc.foreground_color,
            "is_reviewable": pc.is_reviewable,
            "name": "New name",
            "order_index": pc.order_index,
            "tags_ids": ["Q1735684"],
            "organization_code": pc.organization.code,
            "template": {
                "title_placeholder": "NewTitle",
                "description_placeholder": template.description_placeholder,
                "goal_placeholder": template.goal_placeholder,
                "blogentry_placeholder": template.blogentry_placeholder,
            },
        }
        user = UserFactory(
            permissions=[("organizations.change_projectcategory", pc.organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pc.refresh_from_db()
        template = pc.template
        self.assertIsNotNone(template)
        self.assertEqual(template.title_placeholder, "NewTitle")

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_deleting_existing_template(self, mocked):
        mocked.side_effect = self.side_effect
        template = factories.TemplateFactory()
        pc = factories.ProjectCategoryFactory(template=template)
        self.assertIsNotNone(pc.template)

        payload = {
            "background_color": pc.background_color,
            "description": pc.description,
            "foreground_color": pc.foreground_color,
            "is_reviewable": pc.is_reviewable,
            "name": "New name",
            "order_index": pc.order_index,
            "tags_ids": ["Q1735684"],
            "organization_code": pc.organization.code,
        }
        user = UserFactory(
            permissions=[("organizations.change_projectcategory", pc.organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Category-detail", args=(pc.pk,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pc.refresh_from_db()
        self.assertEqual(pc.template.title_placeholder, "")
        self.assertEqual(pc.template.description_placeholder, "")
        self.assertEqual(pc.template.goal_placeholder, "")
        self.assertEqual(pc.template.blogentry_title_placeholder, "")
        self.assertEqual(pc.template.blogentry_placeholder, "")
        self.assertEqual(pc.template.images.count(), 0)
