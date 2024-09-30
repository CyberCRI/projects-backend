import logging
from typing import Collection, List, Union

from algoliasearch_django.decorators import register
from django.conf import settings
from django.db.models import QuerySet
from django.utils.html import strip_tags

from apps.accounts.models import PeopleGroup, PrivacySettings, ProjectUser
from apps.organizations.utils import get_above_hierarchy_codes
from apps.projects.models import Project
from apps.search.models import SearchObject

from .utils import AlgoliaSplittingIndex

TEXT_THRESHOLD = 9000  # 9KB

logger = logging.getLogger(__name__)


class ProjectIndex:
    @staticmethod
    def should_index(project: Project) -> bool:
        """Only index not soft-deleted project."""
        return project.deleted_at is None

    @staticmethod
    def prepare_organizations(project: Project) -> List[str]:
        """Return the organizations' code for Algolia indexing."""
        return get_above_hierarchy_codes(
            [o.code for o in project.get_related_organizations()]
        )

    @staticmethod
    def prepare_permissions(project: Project) -> List[str]:
        """Return all the permissions that give access to this project"""
        if project.publication_status == Project.PublicationStatus.PUBLIC:
            return ["projects.view_public_project"]
        organizations = project.get_related_organizations()
        if project.publication_status == Project.PublicationStatus.ORG:
            return [
                "projects.view_project",
                f"projects.view_project.{project.pk}",
                *[f"organizations.view_project.{org.pk}" for org in organizations],
                *[f"organizations.view_org_project.{org.pk}" for org in organizations],
            ]
        return [
            "projects.view_project",
            f"projects.view_project.{project.pk}",
            *[f"organizations.view_project.{org.pk}" for org in organizations],
        ]

    @staticmethod
    def split_content(project: Project) -> Collection[str]:  # type: ignore
        """Split description every `TEXT_THRESHOLD` bytes.

        HTML is stripped since it can take up a lot of space, and it is
        irrelevant to the search.
        """

        description = strip_tags(project.description)
        blogs = "\n".join(
            [
                f"{entry.title}\n{strip_tags(entry.content)}"
                for entry in project.blog_entries.all()
            ]
        )
        content = "\n".join([description, blogs])

        if len(content) <= TEXT_THRESHOLD:
            yield content
            return

        for i in range(0, len(content), TEXT_THRESHOLD):
            yield content[i : i + TEXT_THRESHOLD]

    @staticmethod
    def prepare_title(project: Project) -> str:
        return project.title

    @staticmethod
    def prepare_subtitle(project: Project) -> str:
        return project.purpose

    @staticmethod
    def prepare_sdgs(project: Project) -> List[int]:
        return project.sdgs

    @staticmethod
    def get_indexing_queryset(self) -> QuerySet:
        """Prefetch relations to speed-up indexing."""
        return self.model.objects.filter(deleted_at=None).prefetch_related(
            "categories",
            "tags",
            "blog_entries",
            "organizations",
        )

    @staticmethod
    def prepare_members(project: Project) -> List[str]:
        """Return the members' names for Algolia indexing."""
        return [
            f"{member.given_name} {member.family_name}"
            for member in project.get_all_members()
        ]

    @staticmethod
    def prepare_categories(project: Project) -> List[str]:
        """Return the categories' name for Algolia indexing."""
        return [category.name for category in project.categories.all()]

    @staticmethod
    def prepare_tags(project: Project) -> List[str]:
        """Return the tags' names for Algolia indexing."""
        return [tag.name for tag in project.tags.all()]

    @staticmethod
    def prepare_language(project: Project) -> str:
        return project.language

    @staticmethod
    def prepare_categories_filter(project: Project) -> List[str]:
        """Return the categores' ids for Algolia indexing."""
        return list(project.categories.all().values_list("id", flat=True))

    @staticmethod
    def prepare_tags_filter(project: Project) -> List[str]:
        """Return the tags' names for Algolia indexing."""
        return list(project.tags.all().values_list("id", flat=True))

    @staticmethod
    def prepare_members_filter(project: Project) -> List[str]:
        """Return the members' names for Algolia indexing."""
        return list(project.get_all_members().values_list("id", flat=True))


class UserIndex:
    @staticmethod
    def should_index(user: ProjectUser) -> bool:
        return True

    @staticmethod
    def prepare_organizations(user: ProjectUser) -> List[str]:
        """Return the organizations' code for Algolia indexing."""
        return [org.code for org in user.get_related_organizations()]

    @staticmethod
    def prepare_permissions(user: ProjectUser) -> List[str]:
        """Return all the permissions that give access to this user"""
        privacy_settings, _ = PrivacySettings.objects.get_or_create(user=user)
        if privacy_settings.publication_status == PrivacySettings.PrivacyChoices.PUBLIC:
            return ["accounts.view_public_projectuser"]
        organizations = user.get_related_organizations()
        if (
            privacy_settings.publication_status
            == PrivacySettings.PrivacyChoices.ORGANIZATION
        ):
            return [
                "accounts.view_projectuser",
                f"accounts.view_projectuser.{user.pk}",
                *[f"organizations.view_projectuser.{org.pk}" for org in organizations],
                *[
                    f"organizations.view_org_projectuser.{org.pk}"
                    for org in organizations
                ],
            ]
        return [
            "accounts.view_projectuser",
            f"accounts.view_projectuser.{user.pk}",
            *[f"organizations.view_projectuser.{org.pk}" for org in organizations],
        ]

    @staticmethod
    def split_content(user: ProjectUser) -> Collection[str]:  # type: ignore
        """Split short_description every `TEXT_THRESHOLD` bytes.

        HTML is stripped since it can take up a lot of space, and it is
        irrelevant to the search.
        """
        description = "\n".join(
            [
                strip_tags(user.short_description),
                strip_tags(user.personal_description),
                strip_tags(user.professional_description),
            ]
        )
        if len(description) <= TEXT_THRESHOLD:
            yield description
            return

        for i in range(0, len(description), TEXT_THRESHOLD):
            yield description[i : i + TEXT_THRESHOLD]

    @staticmethod
    def prepare_title(user: ProjectUser) -> str:
        return user.get_full_name()

    @staticmethod
    def prepare_subtitle(user: ProjectUser) -> str:
        return user.job

    @staticmethod
    def prepare_sdgs(user: ProjectUser) -> List[int]:
        return user.sdgs

    @staticmethod
    def prepare_emails(user: ProjectUser) -> str:
        return [email for email in [user.email, user.personal_email] if email]

    @staticmethod
    def prepare_people_groups(user: ProjectUser) -> List[str]:
        """Return the people groups' names for Algolia indexing."""
        return [
            people_group.name
            for people_group in PeopleGroup.objects.filter(
                groups__users=user
            ).distinct()
        ]

    @staticmethod
    def prepare_projects(user: ProjectUser) -> List[str]:
        """Return the projects' names for Algolia indexing."""
        return [
            project.title
            for project in Project.objects.filter(groups__users=user).distinct()
        ]

    @staticmethod
    def prepare_skills(user: ProjectUser) -> List[str]:
        """Return the skills' names for Algolia indexing."""
        return [skill.tag.title for skill in user.skills_v2.all()]

    @staticmethod
    def prepare_skills_filter(user: ProjectUser) -> List[str]:
        """Return the skills' qids for Algolia filtering."""
        return [skill.tag.id for skill in user.skills_v2.all()]

    @staticmethod
    def prepare_can_mentor_filter(user: ProjectUser) -> bool:
        """Return the skills' qids for Algolia filtering."""
        return user.skills_v2.filter(can_mentor=True).exists()

    @staticmethod
    def prepare_needs_mentor_filter(user: ProjectUser) -> bool:
        """Return the skills' qids for Algolia filtering."""
        return user.skills_v2.filter(needs_mentor=True).exists()

    @staticmethod
    def prepare_can_mentor_on_filter(user: ProjectUser) -> List[str]:
        """Return the skills' qids for Algolia filtering."""
        return [skill.tag.id for skill in user.skills_v2.filter(can_mentor=True)]

    @staticmethod
    def prepare_needs_mentor_on_filter(user: ProjectUser) -> List[str]:
        """Return the skills' qids for Algolia filtering."""
        return [skill.tag.id for skill in user.skills_v2.filter(needs_mentor=True)]


class PeopleGroupIndex:
    @staticmethod
    def should_index(group: PeopleGroup) -> bool:
        """Only index non-root groups."""
        return group.is_root is False

    @staticmethod
    def prepare_organizations(group: PeopleGroup) -> List[str]:
        """Return the organizations' code for Algolia indexing."""
        return [group.organization.code] if group.organization else []

    @staticmethod
    def prepare_permissions(group: PeopleGroup) -> List[str]:
        """Return all the permissions that give access to this group"""
        if group.publication_status == PeopleGroup.PublicationStatus.PUBLIC:
            return ["accounts.view_public_peoplegroup"]
        organizations = group.get_related_organizations()
        if group.publication_status == PeopleGroup.PublicationStatus.ORG:
            return [
                "accounts.view_peoplegroup",
                f"accounts.view_peoplegroup.{group.pk}",
                *[f"organizations.view_peoplegroup.{org.pk}" for org in organizations],
                *[
                    f"organizations.view_org_peoplegroup.{org.pk}"
                    for org in organizations
                ],
            ]
        return [
            "accounts.view_peoplegroup",
            f"accounts.view_peoplegroup.{group.pk}",
            *[f"organizations.view_peoplegroup.{org.pk}" for org in organizations],
        ]

    @staticmethod
    def split_content(group: PeopleGroup) -> Collection[str]:  # type: ignore
        """Split short_description every `TEXT_THRESHOLD` bytes.

        HTML is stripped since it can take up a lot of space, and it is
        irrelevant to the search.
        """
        description = strip_tags(group.description)
        if len(description) <= TEXT_THRESHOLD:
            yield description
            return

        for i in range(0, len(description), TEXT_THRESHOLD):
            yield description[i : i + TEXT_THRESHOLD]

    @staticmethod
    def prepare_title(group: PeopleGroup) -> str:
        return group.name

    @staticmethod
    def prepare_sdgs(group: PeopleGroup) -> List[int]:
        return group.sdgs

    @staticmethod
    def prepare_emails(group: PeopleGroup) -> str:
        return [group.email] if group.email else []

    @staticmethod
    def prepare_is_root(group: PeopleGroup) -> bool:
        return group.is_root


@register(SearchObject)
class SearchObjectIndex(AlgoliaSplittingIndex):
    """
    Class to index any of the above models in a single index.

    This is useful to search for any object in the same query.
    """

    index_name = "mixed_index"
    fields = {
        "unique": (
            # All
            "id",
            "last_update",
            "type",
            "permissions",
            "organizations",
            "sdgs",
            "title",
            "has_organization",
            # Project, User
            "subtitle",
            # User, Group
            "emails",
            # Project
            "members",
            "categories",
            "tags",
            "language",
            "tags_filter",
            "members_filter",
            "categories_filter",
            # User
            "skills",
            "skills_filter",
            "people_groups",
            "projects",
            "can_mentor_filter",
            "needs_mentor_filter",
            "can_mentor_on_filter",
            "needs_mentor_on_filter",
            # Group
            "is_root",
        ),
        "multiple": (
            {
                "id_suffix": "cont",
                "commons": (  # IDs and attributes for faceting
                    # Shared
                    "id",
                    "last_update",
                    "type",
                    "organizations",
                    "permissions",
                    "sdgs",
                    "has_organization",
                    # Project
                    "language",
                    "categories_filter",
                    "members_filter",
                    "tags_filter",
                    # User
                    "skills_filter",
                    "can_mentor_filter",
                    "needs_mentor_filter",
                    "can_mentor_on_filter",
                    "needs_mentor_on_filter",
                    # PeopleGroup
                    "is_root",
                ),
                "split": ("content",),
            },
        ),
    }
    settings = {
        "searchableAttributes": [
            "id",
            "title",
            "subtitle",
            "content",
            "sdgs",
            "emails",
            "members",
            "categories",
            "tags",
            "skills",
            "people_groups",
            "projects",
        ],
        "attributesForFaceting": [
            "organizations",
            "type",
            "filterOnly(has_organization)",
            "filterOnly(is_root)",
            "filterOnly(sdgs)",
            "filterOnly(permissions)",
            "filterOnly(language)",
            "filterOnly(categories_filter)",
            "filterOnly(members_filter)",
            "filterOnly(tags_filter)",
            "filterOnly(skills_filter)",
            "filterOnly(can_mentor_filter)",
            "filterOnly(needs_mentor_filter)",
            "filterOnly(can_mentor_on_filter)",
            "filterOnly(needs_mentor_on_filter)",
        ],
        "customRanking": ["desc(last_update)"],
        "paginationLimitedTo": 5000,
        "hitsPerPage": 10,
        "attributeForDistinct": "id",
        "attributesToRetrieve": ["objectID", "id"],
        "attributesToHighlight": [],
        "separatorsToIndex": "#.%&~£¥$§€<>@-_*",
        # see https://www.algolia.com/doc/api-reference/api-parameters/separatorsToIndex/
        "indexLanguages": settings.REQUIRED_LANGUAGES,
    }

    def get_field_for_model(
        self, search_object: SearchObject, method: str, default: Union[str, List[str]]
    ) -> Union[str, List[str]]:
        match search_object.type:
            case SearchObject.SearchObjectType.PROJECT:
                method = getattr(ProjectIndex, method, None)
            case SearchObject.SearchObjectType.USER:
                method = getattr(UserIndex, method, None)
            case SearchObject.SearchObjectType.PEOPLE_GROUP:
                method = getattr(PeopleGroupIndex, method, None)
            case _:
                method = None
        if method is None:
            return default
        return method(search_object.item)

    def prepare_last_update(self, search_object: SearchObject) -> str:
        if search_object.last_update is None:
            return 0
        return search_object.last_update.timestamp()

    def prepare_type(self, search_object: SearchObject) -> str:
        return search_object.type

    def prepare_permissions(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_permissions", [])

    def prepare_organizations(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_organizations", [])

    def prepare_sdgs(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_sdgs", [])

    def prepare_title(self, search_object: SearchObject) -> str:
        return self.get_field_for_model(search_object, "prepare_title", "")

    def prepare_has_organization(self, search_object: SearchObject) -> bool:
        return bool(
            self.get_field_for_model(search_object, "prepare_organizations", [])
        )

    def prepare_is_root(self, search_object: SearchObject) -> bool:
        return self.get_field_for_model(search_object, "prepare_is_root", False)

    def prepare_subtitle(self, search_object: SearchObject) -> str:
        return self.get_field_for_model(search_object, "prepare_subtitle", "")

    def prepare_emails(self, search_object: SearchObject) -> str:
        return self.get_field_for_model(search_object, "prepare_emails", "")

    def prepare_members(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_members", [])

    def prepare_categories(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_categories", [])

    def prepare_tags(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_tags", [])

    def prepare_language(self, search_object: SearchObject) -> str:
        return self.get_field_for_model(search_object, "prepare_language", "")

    def prepare_tags_filter(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_tags_filter", [])

    def prepare_members_filter(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_members_filter", [])

    def prepare_categories_filter(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_categories_filter", [])

    def prepare_skills(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_skills", [])

    def prepare_skills_filter(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_skills_filter", [])

    def prepare_can_mentor_filter(self, search_object: SearchObject) -> bool:
        return self.get_field_for_model(
            search_object, "prepare_can_mentor_filter", False
        )

    def prepare_needs_mentor_filter(self, search_object: SearchObject) -> bool:
        return self.get_field_for_model(
            search_object, "prepare_needs_mentor_filter", False
        )

    def prepare_can_mentor_on_filter(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(
            search_object, "prepare_can_mentor_on_filter", []
        )

    def prepare_needs_mentor_on_filter(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(
            search_object, "prepare_needs_mentor_on_filter", []
        )

    def prepare_people_groups(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_people_groups", [])

    def prepare_projects(self, search_object: SearchObject) -> List[str]:
        return self.get_field_for_model(search_object, "prepare_projects", [])

    def split_content(self, search_object: SearchObject) -> Collection[str]:
        return self.get_field_for_model(search_object, "split_content", [])
