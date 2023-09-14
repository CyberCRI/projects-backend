from unittest.mock import patch

from django.urls import reverse
from faker import Faker

from apps.accounts.factories import SkillFactory, UserFactory
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase

faker = Faker()


class SkillAnonymousTestCase(JwtAPITestCase, TagTestCase):
    def test_list(self):
        SkillFactory.create_batch(size=3)
        response = self.client.get(reverse("Skill-list"))
        assert response.status_code == 200

    def test_retrieve(self):
        skill = SkillFactory()
        response = self.client.get(reverse("Skill-detail", args=[skill.id]))
        assert response.status_code == 200

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.side_effect
        payload = {
            "user": UserFactory().keycloak_id,
            "wikipedia_tag": "Q1735684",
            "level": 1,
            "level_to_reach": 2,
        }
        response = self.client.post(reverse("Skill-list"), data=payload)
        assert response.status_code == 401

    def test_partial_update(self):
        skill = SkillFactory()
        payload = {
            "level": 2,
        }
        response = self.client.patch(
            reverse("Skill-detail", args=[skill.id]), data=payload
        )
        assert response.status_code == 401

    def test_destroy(self):
        skill = SkillFactory()
        response = self.client.delete(reverse("Skill-detail", args=[skill.id]))
        assert response.status_code == 401


class SkillNoPermissionTestCase(JwtAPITestCase, TagTestCase):
    def test_list(self):
        self.client.force_authenticate(UserFactory())
        SkillFactory.create_batch(size=3)
        response = self.client.get(reverse("Skill-list"))
        assert response.status_code == 200

    def test_retrieve(self):
        self.client.force_authenticate(UserFactory())
        skill = SkillFactory()
        response = self.client.get(reverse("Skill-detail", args=[skill.id]))
        assert response.status_code == 200

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.side_effect
        self.client.force_authenticate(UserFactory())
        payload = {
            "user": UserFactory().keycloak_id,
            "wikipedia_tag": "Q1735684",
            "level": 1,
            "level_to_reach": 2,
        }
        response = self.client.post(reverse("Skill-list"), data=payload)
        assert response.status_code == 403

    def test_partial_update(self):
        self.client.force_authenticate(UserFactory())
        skill = SkillFactory()
        payload = {
            "level": 2,
        }
        response = self.client.patch(
            reverse("Skill-detail", args=[skill.id]), data=payload
        )
        assert response.status_code == 403

    def test_destroy(self):
        self.client.force_authenticate(UserFactory())
        skill = SkillFactory()
        response = self.client.delete(reverse("Skill-detail", args=[skill.id]))
        assert response.status_code == 403


class SkillBasePermissionTestCase(JwtAPITestCase, TagTestCase):
    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.side_effect
        self.client.force_authenticate(
            UserFactory(permissions=[("accounts.change_projectuser", None)])
        )
        payload = {
            "user": UserFactory().keycloak_id,
            "wikipedia_tag": "Q1735684",
            "level": 1,
            "level_to_reach": 2,
        }
        response = self.client.post(reverse("Skill-list"), data=payload)
        assert response.status_code == 201

    def test_partial_update(self):
        self.client.force_authenticate(
            UserFactory(permissions=[("accounts.change_projectuser", None)])
        )
        skill = SkillFactory()
        payload = {
            "level": 2,
        }
        response = self.client.patch(
            reverse("Skill-detail", args=[skill.id]), data=payload
        )
        assert response.status_code == 200

    def test_destroy(self):
        self.client.force_authenticate(
            UserFactory(permissions=[("accounts.change_projectuser", None)])
        )
        skill = SkillFactory()
        response = self.client.delete(reverse("Skill-detail", args=[skill.id]))
        assert response.status_code == 204


class SkillOwnerTestCase(JwtAPITestCase, TagTestCase):
    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create(self, mocked):
        mocked.side_effect = self.side_effect
        user = UserFactory()
        self.client.force_authenticate(user)
        payload = {
            "user": user.keycloak_id,
            "wikipedia_tag": "Q1735684",
            "level": 1,
            "level_to_reach": 2,
        }
        response = self.client.post(reverse("Skill-list"), data=payload)
        assert response.status_code == 201

    def test_partial_update(self):
        skill = SkillFactory()
        self.client.force_authenticate(skill.user)
        payload = {
            "level": 2,
        }
        response = self.client.patch(
            reverse("Skill-detail", args=[skill.id]), data=payload
        )
        assert response.status_code == 200

    def test_destroy(self):
        skill = SkillFactory()
        self.client.force_authenticate(skill.user)
        response = self.client.delete(reverse("Skill-detail", args=[skill.id]))
        assert response.status_code == 204
