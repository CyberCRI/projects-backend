from datetime import date
from typing import Iterable, Optional, Union

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import MultipleObjectsReturned
from django.utils.html import strip_tags
from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.organizations.models import ProjectCategory
from apps.projects.models import Project
from apps.skills.models import Skill, Tag

from .models import SearchObject


@registry.register_document
class UserDocument(Document):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-user"

    class Django:
        model = ProjectUser
        fields = [
            "given_name",
            "family_name",
            "email",
            "personal_email",
            "job",
        ]
        related_models = [
            Tag,
            Skill,
        ]

    search_object_id = fields.IntegerField()
    last_update = fields.DateField()
    content = fields.TextField()
    skills = fields.TextField()
    people_groups = fields.TextField()
    projects = fields.TextField()

    def prepare_search_object_id(self, instance: ProjectUser) -> int:
        try:
            search_object, _ = SearchObject.objects.update_or_create(
                type=SearchObject.SearchObjectType.USER,
                user=instance,
                defaults={"last_update": instance.last_login},
            )
        except MultipleObjectsReturned:
            SearchObject.objects.filter(
                type=SearchObject.SearchObjectType.USER, user=instance
            ).delete()
            return self.prepare_search_object_id(instance)
        return search_object.id

    def prepare_last_update(self, instance: ProjectUser) -> Optional[date]:
        return instance.last_login.date() if instance.last_login else None

    def prepare_content(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                strip_tags(instance.short_description),
                strip_tags(instance.personal_description),
                strip_tags(instance.professional_description),
            ]
        )

    def prepare_skills(self, instance: ProjectUser) -> str:
        return " ".join([skill.tag.title for skill in instance.skills.all()])

    def prepare_people_groups(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                people_group.name
                for people_group in PeopleGroup.objects.filter(groups__users=instance)
            ]
        )

    def prepare_projects(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                project.title
                for project in Project.objects.filter(groups__users=instance)
            ]
        )

    def get_instances_from_related(
        self, related: Union[Tag, Skill]
    ) -> Iterable[ProjectUser]:
        if isinstance(related, Tag):
            return ProjectUser.objects.filter(skills__tag=related).distinct()
        if isinstance(related, Skill):
            return related.user
        return []


@registry.register_document
class PeopleGroupDocument(Document):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-people_group"

    class Django:
        model = PeopleGroup
        fields = [
            "name",
            "email",
        ]
        related_models = [
            Group,
        ]

    search_object_id = fields.IntegerField()
    last_update = fields.DateField()
    content = fields.TextField()
    members = fields.TextField()

    def prepare_search_object_id(self, instance: PeopleGroup) -> int:
        try:
            search_object, _ = SearchObject.objects.update_or_create(
                type=SearchObject.SearchObjectType.PEOPLE_GROUP,
                people_group=instance,
                defaults={"last_update": instance.updated_at},
            )
        except MultipleObjectsReturned:
            SearchObject.objects.filter(
                type=SearchObject.SearchObjectType.PEOPLE_GROUP, people_group=instance
            ).delete()
            return self.prepare_search_object_id(instance)
        return search_object.id

    def prepare_last_update(self, instance: PeopleGroup) -> date:
        return instance.updated_at.date()

    def prepare_content(self, instance: PeopleGroup) -> str:
        return strip_tags(instance.description)

    def prepare_members(self, instance: PeopleGroup) -> str:
        return " ".join(
            [member.get_full_name() for member in instance.get_all_members()]
        )

    def get_instances_from_related(self, related: Group) -> Iterable[PeopleGroup]:
        if isinstance(related, Group):
            return PeopleGroup.objects.filter(groups=related).distinct()
        return []


@registry.register_document
class ProjectDocument(Document):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-project"

    class Django:
        model = Project
        fields = [
            "title",
            "purpose",
        ]
        related_models = [
            ProjectCategory,
            Tag,
            Group,
        ]

    search_object_id = fields.IntegerField()
    last_update = fields.DateField()
    content = fields.TextField()
    members = fields.TextField()
    categories = fields.TextField()
    tags = fields.TextField()

    def prepare_search_object_id(self, instance: Project) -> int:
        try:
            search_object, _ = SearchObject.objects.update_or_create(
                type=SearchObject.SearchObjectType.PROJECT,
                project=instance,
                defaults={"last_update": instance.updated_at},
            )
        except MultipleObjectsReturned:
            SearchObject.objects.filter(
                type=SearchObject.SearchObjectType.PROJECT, project=instance
            ).delete()
            return self.prepare_search_object_id(instance)
        return search_object.id

    def prepare_last_update(self, instance: Project) -> date:
        return instance.updated_at.date()

    def prepare_content(self, instance: Project) -> str:
        return "\n".join(
            [
                strip_tags(instance.description),
                *[
                    f"{entry.title}\n{strip_tags(entry.content)}"
                    for entry in instance.blog_entries.all()
                ],
            ]
        )

    def prepare_members(self, instance: Project) -> str:
        return " ".join(
            [member.get_full_name() for member in instance.get_all_members()]
        )

    def prepare_categories(self, instance: Project) -> str:
        return " ".join([category.name for category in instance.categories.all()])

    def prepare_tags(self, instance: Project) -> str:
        return " ".join([tag.title for tag in instance.tags.all()])

    def get_instances_from_related(
        self, related: Union[ProjectCategory, Tag, Group]
    ) -> Iterable[Project]:
        if isinstance(related, ProjectCategory):
            return Project.objects.filter(categories=related).distinct()
        if isinstance(related, Tag) and related.type == Tag.TagType.CUSTOM:
            return Project.objects.filter(tags=related).distinct()
        if isinstance(related, Group):
            return Project.objects.filter(groups=related).distinct()
        return []


@registry.register_document
class TagDocument(Document):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-tag"

    class Django:
        model = Tag
        fields = ["id"]

    title_fr = fields.TextField()
    title_en = fields.TextField()
    description_fr = fields.TextField()
    description_en = fields.TextField()

    def prepare_title_fr(self, instance: Tag) -> str:
        return instance.title_fr

    def prepare_title_en(self, instance: Tag) -> str:
        return instance.title_en

    def prepare_description_fr(self, instance: Tag) -> str:
        return instance.description_fr

    def prepare_description_en(self, instance: Tag) -> str:
        return instance.description_en
