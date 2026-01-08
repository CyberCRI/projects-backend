from datetime import date
from typing import Iterable, Optional, Union

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import MultipleObjectsReturned
from django.db import models
from django.utils.html import strip_tags
from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.organizations.models import ProjectCategory
from apps.projects.models import Project
from apps.skills.models import Skill, Tag

from .models import SearchObject


class TranslatedDocument(Document):
    """
    Base document with helper methods for translated fields.
    """

    def _get_field_translation(
        self, instance: models.Model, field_name: str, lang: str, html: bool = False
    ) -> str:
        field_value = getattr(instance, f"{field_name}_{lang}", "") or ""
        if html and field_value:
            field_value = strip_tags(field_value)
        return field_value

    def prepare_translated_field(
        self, instance: models.Model, field_name: str, html: bool = False
    ) -> str:
        return " ".join(
            [
                self._get_field_translation(instance, field_name, lang, html)
                for lang in settings.REQUIRED_LANGUAGES
            ]
        )

    def prepare_auto_translated_field(
        self, instance: models.Model, field_name: str, html: bool = False
    ) -> str:
        original_field = getattr(instance, field_name, "") or ""
        if html and original_field:
            original_field = strip_tags(original_field)
        return " ".join(
            [
                original_field,
                self.prepare_translated_field(instance, field_name, html),
            ]
        )


@registry.register_document
class UserDocument(TranslatedDocument):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-user"

    class Django:
        model = ProjectUser
        fields = [
            "id",
            "given_name",
            "family_name",
            "email",
            "personal_email",
        ]
        related_models = [
            Tag,
            Skill,
        ]

    search_object_id = fields.IntegerField()
    last_update = fields.DateField()
    job = fields.TextField()
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

    def prepare_job(self, instance: ProjectUser) -> str:
        return self.prepare_auto_translated_field(instance, "job")

    def prepare_content(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                self.prepare_auto_translated_field(
                    instance, "short_description", html=True
                ),
                self.prepare_auto_translated_field(instance, "description", html=True),
            ]
        )

    def prepare_skills(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                self.prepare_translated_field(skill.tag, "title")
                for skill in instance.skills.all()
            ]
        )

    def prepare_people_groups(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                self.prepare_auto_translated_field(people_group, "name")
                for people_group in PeopleGroup.objects.filter(groups__users=instance)
            ]
        )

    def prepare_projects(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                self.prepare_auto_translated_field(project, "title")
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
class PeopleGroupDocument(TranslatedDocument):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-people_group"

    class Django:
        model = PeopleGroup
        fields = [
            "id",
            "email",
        ]
        related_models = [
            Group,
        ]

    search_object_id = fields.IntegerField()
    last_update = fields.DateField()
    name = fields.TextField()
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

    def prepare_name(self, instance: PeopleGroup) -> str:
        return self.prepare_auto_translated_field(instance, "name")

    def prepare_content(self, instance: PeopleGroup) -> str:
        return self.prepare_auto_translated_field(instance, "description", html=True)

    def prepare_members(self, instance: PeopleGroup) -> str:
        return " ".join(
            [member.get_full_name() for member in instance.get_all_members()]
        )

    def get_instances_from_related(self, related: Group) -> Iterable[PeopleGroup]:
        if isinstance(related, Group):
            return PeopleGroup.objects.filter(groups=related).distinct()
        return []


@registry.register_document
class ProjectDocument(TranslatedDocument):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-project"

    class Django:
        model = Project
        fields = [
            "id",
        ]
        related_models = [
            ProjectCategory,
            Tag,
            Group,
        ]

    search_object_id = fields.IntegerField()
    last_update = fields.DateField()
    title = fields.TextField()
    purpose = fields.TextField()
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

    def prepare_title(self, instance: Project) -> str:
        return self.prepare_auto_translated_field(instance, "title")

    def prepare_purpose(self, instance: Project) -> str:
        return self.prepare_auto_translated_field(instance, "purpose")

    def prepare_content(self, instance: Project) -> str:
        return "\n".join(
            [
                self.prepare_auto_translated_field(instance, "description", html=True),
                *[
                    f"{self.prepare_auto_translated_field(entry, 'title')}\n"
                    f"{self.prepare_auto_translated_field(entry, 'content', html=True)}"
                    for entry in instance.blog_entries.all()
                ],
            ]
        )

    def prepare_members(self, instance: Project) -> str:
        return " ".join(
            [member.get_full_name() for member in instance.get_all_members()]
        )

    def prepare_categories(self, instance: Project) -> str:
        return " ".join(
            [
                self.prepare_auto_translated_field(category, "title")
                for category in instance.categories.all()
            ]
        )

    def prepare_tags(self, instance: Project) -> str:
        return " ".join(
            [self.prepare_translated_field(tag, "title") for tag in instance.tags.all()]
        )

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
class TagDocument(TranslatedDocument):
    class Index:
        name = f"{settings.OPENSEARCH_INDEX_PREFIX}-tag"
        settings = {
            "max_terms_count": 100000,
        }

    class Django:
        model = Tag
        fields = ["id"]

    title = fields.TextField()
    content = fields.TextField()
    alternative_titles = fields.TextField()

    def prepare_title(self, instance: Tag) -> str:
        return self.prepare_translated_field(instance, "title")

    def prepare_content(self, instance: Tag) -> str:
        return self.prepare_translated_field(instance, "description")

    def prepare_alternative_titles(self, instance: Tag) -> str:
        return self.prepare_translated_field(instance, "alternative_titles")
