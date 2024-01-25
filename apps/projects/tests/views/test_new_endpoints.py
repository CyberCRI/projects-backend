from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.organizations.models import Organization
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


# TODO : django-guardian rework move these tests to other files
class TestProjectMembersTempFileTestCase(JwtAPITestCase):
    def test_add_members_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        member_to_owner = UserFactory()
        project.members.add(member_to_owner)
        member = UserFactory()
        reviewer = UserFactory()
        owner = UserFactory()
        people_group = PeopleGroupFactory()
        payload = {
            "members": [member.keycloak_id],
            "reviewers": [reviewer.keycloak_id],
            "owners": [owner.keycloak_id, member_to_owner.keycloak_id],
            "people_groups": [people_group.id],
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member in project.members.all()
        assert reviewer in project.reviewers.all()
        assert owner in project.owners.all()
        assert member_to_owner in project.owners.all()
        assert member_to_owner not in project.members.all()
        assert people_group in project.member_people_groups.all()
        assert all(
            member in project.member_people_groups_members.all()
            for member in people_group.get_all_members()
        )

    def test_remove_members_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        member = UserFactory()
        reviewer = UserFactory()
        owner = UserFactory()
        people_group = PeopleGroupFactory()
        project.members.add(member)
        project.reviewers.add(reviewer)
        project.owners.add(owner)
        project.people_groups.add(people_group)
        project.set_people_group_members()

        payload = {
            "users": [owner.keycloak_id, reviewer.keycloak_id, member.keycloak_id],
            "people_groups": [people_group.id],
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member not in project.members.all()
        assert reviewer not in project.reviewers.all()
        assert owner not in project.owners.all()
        assert people_group not in project.member_people_groups.all()
        assert all(
            member not in project.member_people_groups_members.all()
            for member in people_group.get_all_members()
        )

    def test_remove_members_retrocompatibility(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        member = UserFactory(groups=[project.get_members()])
        reviewer = UserFactory(groups=[project.get_reviewers()])
        owner = UserFactory(groups=[project.get_owners()])

        assert member in project.members.all()
        assert reviewer in project.reviewers.all()
        assert owner in project.owners.all()

        user = UserFactory()
        user.groups.add(get_superadmins_group())

        payload = {
            "user": member.keycloak_id,
            "name": "members",
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member not in project.members.all()

        payload = {
            "user": reviewer.keycloak_id,
            "name": "reviewers",
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        assert reviewer not in project.reviewers.all()

        payload = {
            "user": owner.keycloak_id,
            "name": "owners",
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        assert owner not in project.owners.all()

    def test_create_with_members(self):
        fake = ProjectFactory.build()
        organization = OrganizationFactory()
        category = ProjectCategoryFactory(organization=organization)
        members = UserFactory.create_batch(3)
        reviewers = UserFactory.create_batch(3)
        owners = UserFactory.create_batch(3)
        people_groups = PeopleGroupFactory.create_batch(3)
        payload = {
            "organizations_codes": [organization.code],
            "title": fake.title,
            "description": fake.description,
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": [category.id],
            "organization_tags_ids": [],
            "images_ids": [],
            "team": {
                "members": [m.keycloak_id for m in members],
                "reviewers": [r.keycloak_id for r in reviewers],
                "owners": [o.keycloak_id for o in owners],
                "people_groups": [p.id for p in people_groups],
            },
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Project-list"), data=payload)
        assert response.status_code == status.HTTP_201_CREATED
        project = Project.objects.get(id=response.data["id"])
        assert user in project.owners.all()
        assert all(member in project.members.all() for member in members)
        assert all(reviewer in project.reviewers.all() for reviewer in reviewers)
        assert all(owner in project.owners.all() for owner in owners)
        assert all(
            people_group in project.member_people_groups.all()
            for people_group in people_groups
        )
        assert all(
            member in project.pmember_people_groups_members.all()
            for people_group in people_groups
            for member in people_group.get_all_members()
        )


class TestOrganizationMembersTempFileTestCase(JwtAPITestCase):
    def test_add_members_base_permission(self):
        organization = OrganizationFactory()
        admin = UserFactory()
        user = UserFactory()
        facilitator = UserFactory()
        user_to_admin = UserFactory()
        organization.users.add(user_to_admin)
        payload = {
            "users": [user.keycloak_id],
            "admins": [admin.keycloak_id, user_to_admin.keycloak_id],
            "facilitators": [facilitator.keycloak_id],
        }
        request_user = UserFactory()
        request_user.groups.add(get_superadmins_group())
        self.client.force_authenticate(request_user)
        response = self.client.post(
            reverse("Organization-add-member", args=(organization.code,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert user in organization.users.all()
        assert admin in organization.admins.all()
        assert facilitator in organization.facilitators.all()
        assert user_to_admin in organization.admins.all()
        assert user_to_admin not in organization.users.all()

    def test_remove_members_base_permission(self):
        organization = OrganizationFactory()
        admin = UserFactory()
        user = UserFactory()
        facilitator = UserFactory()
        organization.admins.add(admin)
        organization.users.add(user)
        organization.facilitators.add(facilitator)
        payload = {
            "users": [user.keycloak_id, admin.keycloak_id, facilitator.keycloak_id],
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Organization-remove-member", args=(organization.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert user not in organization.users.all()
        assert admin not in organization.admins.all()
        assert facilitator not in organization.facilitators.all()

    def test_create_with_members(self):
        organization = OrganizationFactory()
        admins = UserFactory.create_batch(5)
        users = UserFactory.create_batch(5)
        facilitators = UserFactory.create_batch(5)
        fake = OrganizationFactory.build()
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
            "wikipedia_tags_ids": [],
            "parent_code": parent.code,
            "team": {
                "users": [u.keycloak_id for u in users],
                "admins": [a.keycloak_id for a in admins],
                "facilitators": [f.keycloak_id for f in facilitators],
            },
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Organization-list"), payload)
        assert response.status_code == status.HTTP_201_CREATED
        organization = Organization.objects.get(code=response.json()["code"])
        assert all(u in organization.users.all() for u in users)
        assert all(a in organization.admins.all() for a in admins)
        assert all(f in organization.facilitators.all() for f in facilitators)
