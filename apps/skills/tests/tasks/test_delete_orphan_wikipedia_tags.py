from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.skills.factories import SkillFactory, TagClassificationFactory, TagFactory
from apps.skills.models import Tag
from apps.skills.tasks import delete_orphan_wikipedia_tags
from services.mistral.factories import TagEmbeddingFactory

faker = Faker()


class DeleteOrphanWikipediaTagsTestCase(JwtAPITestCase):
    def test_delete_orphan_wikipedia_tags(self):
        organization = OrganizationFactory()
        category = ProjectCategoryFactory(organization=organization)
        project = ProjectFactory(organizations=[organization])
        user = UserFactory()
        date = timezone.localtime(timezone.now()) - timedelta(
            seconds=settings.TAG_ORPHAN_THRESHOLD_SECONDS
        )

        tags = {}
        for tag_type in Tag.TagType.values:
            classification = TagClassificationFactory(
                organization=organization, type=tag_type
            )
            orphan = TagFactory(type=tag_type)
            orphan_outdated = TagFactory(type=tag_type)
            orphan_outdated.created_at = date
            orphan_outdated.save()

            project_linked = TagFactory(type=tag_type)
            project_linked_outdated = TagFactory(type=tag_type)
            project_linked_outdated.created_at = date
            project_linked_outdated.save()
            project.tags.add(project_linked, project_linked_outdated)

            skill_linked = TagFactory(type=tag_type)
            skill_linked_outdated = TagFactory(type=tag_type)
            skill_linked_outdated.created_at = date
            skill_linked_outdated.save()
            SkillFactory(user=user, tag=skill_linked)
            SkillFactory(user=user, tag=skill_linked_outdated)

            category_linked = TagFactory(type=tag_type)
            category_linked_outdated = TagFactory(type=tag_type)
            category_linked_outdated.created_at = date
            category_linked_outdated.save()
            category.tags.add(category_linked, category_linked_outdated)

            org_project_linked = TagFactory(type=tag_type)
            org_project_linked_outdated = TagFactory(type=tag_type)
            org_project_linked_outdated.created_at = date
            org_project_linked_outdated.save()
            organization.default_projects_tags.add(
                org_project_linked, org_project_linked_outdated
            )

            org_skill_linked = TagFactory(type=tag_type)
            org_skill_linked_outdated = TagFactory(type=tag_type)
            org_skill_linked_outdated.created_at = date
            org_skill_linked_outdated.save()
            organization.default_skills_tags.add(
                org_skill_linked, org_skill_linked_outdated
            )

            created_tags = {
                "orphan": orphan,
                "orphan_outdated": orphan_outdated,
                "project_linked": project_linked,
                "project_linked_outdated": project_linked_outdated,
                "skill_linked": skill_linked,
                "skill_linked_outdated": skill_linked_outdated,
                "category_linked": category_linked,
                "category_linked_outdated": category_linked_outdated,
                "org_project_linked": org_project_linked,
                "org_project_linked_outdated": org_project_linked_outdated,
                "org_skill_linked": org_skill_linked,
                "org_skill_linked_outdated": org_skill_linked_outdated,
            }
            for tag in created_tags.values():
                TagEmbeddingFactory(item=tag)
            tags[tag_type] = created_tags

            classification.tags.add(*tags[tag_type].values())

        deleted = delete_orphan_wikipedia_tags()

        self.assertEqual(deleted, [tags[Tag.TagType.WIKIPEDIA]["orphan_outdated"].id])
        self.assertEqual(Tag.objects.filter(type=Tag.TagType.WIKIPEDIA).count(), 11)
        self.assertEqual(Tag.objects.filter(type=Tag.TagType.ESCO).count(), 12)
        self.assertEqual(Tag.objects.filter(type=Tag.TagType.CUSTOM).count(), 12)
        self.assertFalse(
            Tag.objects.filter(
                id=tags[Tag.TagType.WIKIPEDIA]["orphan_outdated"].id
            ).exists()
        )
