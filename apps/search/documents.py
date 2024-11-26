from typing import Iterable, Union
from django.db.models.query import QuerySet
from django.utils.html import strip_tags

from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry

from apps.projects.models import Project
from apps.organizations.models import ProjectCategory
from apps.skills.models import Tag, Skill
from django.contrib.auth.models import Group
from apps.accounts.models import ProjectUser, PeopleGroup
from .models import SearchObject


@registry.register_document
class UserDocument(Document):
    class Index:
        name = "users"

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

    content = fields.TextField()
    people_groups = fields.TextField()
    projects = fields.TextField()

    def prepare_content(self, instance: ProjectUser) -> str:
        return " ".join(
            [
                strip_tags(instance.short_description),
                strip_tags(instance.personal_description),
                strip_tags(instance.professional_description),
            ]
        )

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
    
    def get_instances_from_related(self, related: Union[Tag, Skill]) -> Iterable[ProjectUser]:
        if isinstance(related, Tag):
            return ProjectUser.objects.filter(skills__tag=related)
        if isinstance(related, Skill):
            return [related.user]
        return []


@registry.register_document
class PeopleGroupDocument(Document):
    class Index:
        name = "people_groups"

    class Django:
        model = PeopleGroup
        fields = [
            "name",
            "description",
            "email",
        ]
        related_models = [
            Group,
        ]

    content = fields.TextField()
    members = fields.TextField()
    
    def prepare_content(self, instance: PeopleGroup) -> str:
        return strip_tags(instance.description)
    
    def prepare_members(self, instance: PeopleGroup) -> str:
        return " ".join([member.get_full_name() for member in instance.get_all_members()])
    
    def get_instances_from_related(self, related: Group) -> Iterable[PeopleGroup]:
        if isinstance(related, Group):
            return PeopleGroup.objects.filter(groups=related)
        return []


@registry.register_document
class ProjectDocument(Document):
    class Index:
        name = "projects"

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

    content = fields.TextField()
    members = fields.TextField()
    categories = fields.TextField()
    tags = fields.TextField()
    
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
        return " ".join([member.get_full_name() for member in instance.get_all_members()])
    
    def prepare_categories(self, instance: Project) -> str:
        return " ".join(
            [category.name for category in instance.categories.all()]
        )
    
    def prepare_tags(self, instance: Project) -> str:
        return " ".join([tag.title for tag in instance.tags.all()])
    
    def get_instances_from_related(self, related: Union[ProjectCategory, Tag, Group]) -> Iterable[Project]:
        if isinstance(related, ProjectCategory):
            return Project.objects.filter(categories=related)
        if isinstance(related, Tag):
            return Project.objects.filter(tags=related)
        if isinstance(related, Group):
            return Project.objects.filter(groups=related)
        return []
