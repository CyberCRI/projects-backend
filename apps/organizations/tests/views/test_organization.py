from unittest.mock import patch

from dateutil.parser import parse as parse_date
from django.conf import settings
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization


class OrganizationTestCaseAnonymous(JwtAPITestCase, TagTestCase):
    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_anonymous(self, mocked):
        mocked.side_effect = self.side_effect
        fake = OrganizationFactory.build()
        parent = OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": fake.background_color,
            "code": fake.code,
            "contact_email": fake.contact_email,
            "dashboard_title": fake.dashboard_title,
            "dashboard_subtitle": fake.dashboard_subtitle,
            "language": fake.language,
            "logo_image_id": fake.logo_image.id,
            "is_logo_visible_on_parent_dashboard": fake.is_logo_visible_on_parent_dashboard,
            "name": fake.name,
            "website_url": fake.website_url,
            "created_at": fake.created_at,
            "updated_at": fake.updated_at,
            "wikipedia_tags_ids": wikipedia_tags,
            "parent_code": parent.code,
        }
        response = self.client.post(reverse("Organization-list"), data=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_anonymous(self):
        orga = OrganizationFactory()
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert "parent_code" in response.data
        assert "children" in response.data

    def test_list_anonymous(self):
        orgas = OrganizationFactory.create_batch(2)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Organization-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual({o.id for o in orgas}, {o["id"] for o in content["results"]})

    def test_destroy_anonymous(self):
        orga = OrganizationFactory()
        response = self.client.delete(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_anonymous(self, mocked):
        mocked.side_effect = self.side_effect
        orga = OrganizationFactory()
        parent = OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": orga.background_color,
            "code": "NewCode",
            "contact_email": orga.contact_email,
            "dashboard_title": orga.dashboard_title,
            "dashboard_subtitle": orga.dashboard_subtitle,
            "language": orga.language,
            "logo_image_id": orga.logo_image.id,
            "is_logo_visible_on_parent_dashboard": orga.is_logo_visible_on_parent_dashboard,
            "name": orga.name,
            "website_url": orga.website_url,
            "created_at": orga.created_at,
            "updated_at": orga.updated_at,
            "wikipedia_tags_ids": wikipedia_tags,
            "parent_code": parent.code,
        }
        response = self.client.put(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partial_update_anonymous(self):
        orga = OrganizationFactory()
        payload = {
            "code": "NewCode",
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OrganizationTestCaseNoPermission(JwtAPITestCase, TagTestCase):
    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_no_permission(self, mocked):
        mocked.side_effect = self.side_effect
        fake = OrganizationFactory.build()
        wikipedia_tags = ["Q1735684"]
        parent = OrganizationFactory()
        payload = {
            "background_color": fake.background_color,
            "code": fake.code,
            "contact_email": fake.contact_email,
            "dashboard_title": fake.dashboard_title,
            "dashboard_subtitle": fake.dashboard_subtitle,
            "language": fake.language,
            "logo_image_id": fake.logo_image.id,
            "is_logo_visible_on_parent_dashboard": fake.is_logo_visible_on_parent_dashboard,
            "name": fake.name,
            "website_url": fake.website_url,
            "created_at": fake.created_at,
            "wikipedia_tags_ids": wikipedia_tags,
            "parent_code": parent.code,
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Organization-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_no_permission(self):
        orga = OrganizationFactory()
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_no_permission(self):
        orgas = OrganizationFactory.create_batch(2)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Organization-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual({o.id for o in orgas}, {o["id"] for o in content["results"]})

    def test_destroy_no_permission(self):
        orga = OrganizationFactory()
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_no_permission(self, mocked):
        mocked.side_effect = self.side_effect
        orga = OrganizationFactory()
        parent = OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": orga.background_color,
            "code": "NewCode",
            "contact_email": orga.contact_email,
            "dashboard_title": orga.dashboard_title,
            "dashboard_subtitle": orga.dashboard_subtitle,
            "language": orga.language,
            "logo_image_id": orga.logo_image.id,
            "is_logo_visible_on_parent_dashboard": orga.is_logo_visible_on_parent_dashboard,
            "name": orga.name,
            "website_url": orga.website_url,
            "created_at": orga.created_at,
            "updated_at": orga.updated_at,
            "wikipedia_tags_ids": wikipedia_tags,
            "parent_code": parent.code,
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.put(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_no_permission(self):
        orga = OrganizationFactory()
        payload = {
            "code": "NewCode",
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OrganizationTestBasePermission(JwtAPITestCase, TagTestCase):
    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_base_permission(self, mocked):
        mocked.side_effect = self.side_effect
        fake = OrganizationFactory.build()
        wikipedia_tags = ["Q1735684"]
        parent = OrganizationFactory()
        payload = {
            "background_color": fake.background_color,
            "code": fake.code,
            "contact_email": fake.contact_email,
            "dashboard_title": fake.dashboard_title,
            "dashboard_subtitle": fake.dashboard_subtitle,
            "language": fake.language,
            "logo_image_id": fake.logo_image.id,
            "is_logo_visible_on_parent_dashboard": fake.is_logo_visible_on_parent_dashboard,
            "name": fake.name,
            "website_url": fake.website_url,
            "created_at": fake.created_at,
            "updated_at": fake.updated_at,
            "wikipedia_tags_ids": wikipedia_tags,
            "parent_code": parent.code,
        }
        user = UserFactory(permissions=[("organizations.add_organization", None)])
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Organization-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        content = response.json()
        self.assertIn("id", content)

        organization = Organization.objects.get(id=content["id"])
        self.assertEqual(fake.background_color, organization.background_color)
        self.assertEqual(fake.code, organization.code)
        self.assertEqual(fake.contact_email, organization.contact_email)
        self.assertEqual(fake.dashboard_title, organization.dashboard_title)
        self.assertEqual(fake.dashboard_subtitle, organization.dashboard_subtitle)
        self.assertEqual(fake.language, organization.language)
        self.assertEqual(fake.logo_image.id, organization.logo_image.id)
        self.assertEqual(
            fake.is_logo_visible_on_parent_dashboard,
            organization.is_logo_visible_on_parent_dashboard,
        )
        self.assertEqual(fake.name, organization.name)
        self.assertEqual(fake.website_url, organization.website_url)
        self.assertEqual(
            wikipedia_tags,
            list(
                organization.wikipedia_tags.all().values_list(
                    "wikipedia_qid", flat=True
                )
            ),
        )
        self.assertEqual(parent.code, organization.parent.code)

    def test_retrieve_base_permission(self):
        orga = OrganizationFactory()
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(orga.background_color, content["background_color"])
        self.assertEqual(orga.code, content["code"])
        self.assertEqual(orga.contact_email, content["contact_email"])
        self.assertEqual(orga.dashboard_title, content["dashboard_title"])
        self.assertEqual(orga.dashboard_subtitle, content["dashboard_subtitle"])
        self.assertEqual(orga.language, content["language"])
        self.assertEqual(orga.logo_image.id, content["logo_image"]["id"])
        self.assertEqual(
            orga.is_logo_visible_on_parent_dashboard,
            content["is_logo_visible_on_parent_dashboard"],
        )
        self.assertEqual(orga.name, content["name"])
        self.assertEqual(orga.website_url, content["website_url"])
        self.assertEqual(
            list(orga.wikipedia_tags.all().values_list("wikipedia_qid", flat=True)),
            list([t["wikipedia_qid"] for t in content["wikipedia_tags"]]),
        )

    def test_list_base_permission(self):
        orgas = OrganizationFactory.create_batch(2)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Organization-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual({o.id for o in orgas}, {o["id"] for o in content["results"]})

    def test_destroy_base_permission(self):
        orga = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.delete_organization", None)])
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Organization.objects.filter(code=orga.code).exists())

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_base_permission(self, mocked):
        mocked.side_effect = self.side_effect
        orga = OrganizationFactory()
        parent = OrganizationFactory()
        wikipedia_tags = ["Q1735684"]
        payload = {
            "background_color": orga.background_color,
            "code": "NewCode",
            "contact_email": orga.contact_email,
            "dashboard_title": orga.dashboard_title,
            "dashboard_subtitle": orga.dashboard_subtitle,
            "language": orga.language,
            "logo_image_id": orga.logo_image.id,
            "is_logo_visible_on_parent_dashboard": orga.is_logo_visible_on_parent_dashboard,
            "name": orga.name,
            "website_url": orga.website_url,
            "created_at": orga.created_at,
            "updated_at": orga.updated_at,
            "wikipedia_tags_ids": wikipedia_tags,
            "parent_code": parent.code,
        }
        user = UserFactory(permissions=[("organizations.change_organization", None)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        orga.refresh_from_db()
        self.assertEqual(orga.code, "NewCode")

    def test_partial_update_base_permission(self):
        orga = OrganizationFactory()
        payload = {"code": "NewCode"}
        user = UserFactory(permissions=[("organizations.change_organization", None)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orga.refresh_from_db()
        self.assertEqual(orga.code, "NewCode")


class OrganizationTestOrganizationPermission(JwtAPITestCase, TagTestCase):
    def test_retrieve_organization_permission(self):
        orga = OrganizationFactory()
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(orga.background_color, content["background_color"])
        self.assertEqual(orga.code, content["code"])
        self.assertEqual(orga.contact_email, content["contact_email"])
        self.assertEqual(orga.dashboard_title, content["dashboard_title"])
        self.assertEqual(orga.dashboard_subtitle, content["dashboard_subtitle"])
        self.assertEqual(orga.language, content["language"])
        self.assertEqual(orga.logo_image.id, content["logo_image"]["id"])
        self.assertEqual(orga.name, content["name"])
        self.assertEqual(orga.website_url, content["website_url"])
        self.assertEqual(orga.created_at, parse_date(content["created_at"]))
        self.assertEqual(orga.updated_at, parse_date(content["updated_at"]))
        self.assertEqual(
            list(orga.wikipedia_tags.all().values_list("wikipedia_qid", flat=True)),
            list([t["wikipedia_qid"] for t in content["tags"]]),
        )

    def test_list_organization_permission(self):
        orgas = OrganizationFactory.create_batch(2)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Organization-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual({o.id for o in orgas}, {o["id"] for o in content["results"]})

    def test_destroy_organization_permission(self):
        orga = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.delete_organization", orga)])
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Organization-detail", args=(orga.code,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Organization.objects.filter(code=orga.code).exists())

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_organization_permission(self, mocked):
        mocked.side_effect = self.side_effect
        orga = OrganizationFactory()
        payload = {
            "background_color": orga.background_color,
            "code": "NewCode",
            "contact_email": orga.contact_email,
            "dashboard_title": orga.dashboard_title,
            "dashboard_subtitle": orga.dashboard_subtitle,
            "language": orga.language,
            "logo_image_id": orga.logo_image.id,
            "name": orga.name,
            "website_url": orga.website_url,
            "created_at": orga.created_at,
            "updated_at": orga.updated_at,
            "tags_ids": ["Q1735684"],
        }
        user = UserFactory(permissions=[("organizations.change_organization", orga)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        assert response.status_code == status.HTTP_200_OK
        orga.refresh_from_db()
        self.assertEqual(orga.code, "NewCode")

    def test_partial_update_organization_permission(self):
        orga = OrganizationFactory()
        payload = {"code": "NewCode"}
        user = UserFactory(permissions=[("organizations.change_organization", orga)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", args=(orga.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orga.refresh_from_db()
        self.assertEqual(orga.code, "NewCode")


class OrganizationTestCase(JwtAPITestCase):
    def test_add_member(self):
        organization = OrganizationFactory()
        admin = UserFactory()
        facilitator = UserFactory()
        new_user = UserFactory()
        user = UserFactory()
        organization.users.add(user)
        organization.admins.add(user)
        self.client.force_authenticate(user)

        payload = {
            Organization.DefaultGroup.ADMINS: [admin.keycloak_id],
        }
        response = self.client.post(
            reverse("Organization-add-member", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert admin in organization.admins.all()
        assert admin in organization.get_all_members().all()

        payload = {
            Organization.DefaultGroup.FACILITATORS: [facilitator.keycloak_id],
        }
        response = self.client.post(
            reverse("Organization-add-member", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert facilitator in organization.facilitators.all()
        assert admin in organization.get_all_members().all()

        payload = {
            Organization.DefaultGroup.USERS: [new_user.keycloak_id],
        }
        response = self.client.post(
            reverse("Organization-add-member", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert new_user in organization.users.all()
        assert new_user in organization.get_all_members().all()

    def test_change_member_role(self):
        organization = OrganizationFactory()
        user = UserFactory()
        to_update = UserFactory()
        organization.users.add(user, to_update)
        organization.admins.add(user)
        organization.users.add(to_update)
        self.client.force_authenticate(user)

        payload = {
            Organization.DefaultGroup.FACILITATORS: [to_update.keycloak_id],
        }
        response = self.client.post(
            reverse("Organization-add-member", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert to_update in organization.facilitators.all()
        assert to_update not in organization.users.all()
        assert to_update in organization.get_all_members().all()

    def test_remove_member(self):
        organization = OrganizationFactory()
        admin = UserFactory()
        facilitator = UserFactory()
        user = UserFactory()

        organization.admins.add(admin)
        organization.facilitators.add(facilitator)
        organization.users.add(user)

        user2 = UserFactory()
        organization.admins.add(user2)
        self.client.force_authenticate(user2)

        payload = {
            "users": [admin.keycloak_id],
        }
        response = self.client.post(
            reverse("Organization-remove-member", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert admin not in organization.admins.all()
        assert admin not in organization.get_all_members().all()

        payload = {
            "users": [facilitator.keycloak_id],
        }
        response = self.client.post(
            reverse("Organization-remove-member", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert facilitator not in organization.facilitators.all()
        assert facilitator not in organization.get_all_members().all()

        payload = {
            "users": [user.keycloak_id],
        }
        response = self.client.post(
            reverse("Organization-remove-member", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert user not in organization.users.all()
        assert user not in organization.get_all_members().all()

    def test_google_sync_enabled(self):
        organization = OrganizationFactory()
        synced_organization = OrganizationFactory(
            code=settings.GOOGLE_SYNCED_ORGANIZATION
        )
        response = self.client.get(
            reverse("Organization-detail", args=(organization.code,))
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["google_sync_enabled"] is False
        response = self.client.get(
            reverse("Organization-detail", args=(synced_organization.code,))
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["google_sync_enabled"] is True

    def test_roles_are_deleted_on_organization_delete(self):
        organization = OrganizationFactory()
        roles_names = [r.name for r in organization.groups.all()]
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Organization-detail",
                args=(organization.code,),
            )
        )
        assert response.status_code == 204
        assert not Group.objects.filter(name__in=roles_names).exists()
