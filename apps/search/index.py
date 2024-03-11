import logging
from typing import Collection, List

from algoliasearch_django.decorators import register
from django.conf import settings
from django.db.models import QuerySet
from django.utils.html import strip_tags

from apps.accounts.models import PeopleGroup, PrivacySettings, ProjectUser
from apps.projects.models import Project

from .utils import AlgoliaSplittingIndex

TEXT_THRESHOLD = 9000  # 9KB

logger = logging.getLogger(__name__)


@register(Project)
class ProjectIndex(AlgoliaSplittingIndex):
    """Algolia index definition for `Project`."""

    index_name = "project"
    fields = {
        "unique": (
            "id",
            "title",
            "purpose",
            "members",
            "categories",
            "wikipedia_tags",
            "organization_tags",
            "organizations",
            "sdgs",
            "language",
            "wikipedia_tags_filter",
            "organization_tags_filter",
            "members_filter",
            "categories_filter",
            "permissions",
        ),
        "multiple": (
            {
                "id_suffix": "desc",
                "commons": (  # IDs and attributes for faceting
                    "id",
                    "organizations",
                    "language",
                    "sdgs",
                    "categories_filter",
                    "members_filter",
                    "wikipedia_tags_filter",
                    "organization_tags_filter",
                    "permissions",
                ),
                "split": ("description",),
            },
            {
                "id_suffix": "blog",
                "commons": (  # IDs and attributes for faceting
                    "id",
                    "organizations",
                    "language",
                    "sdgs",
                    "categories_filter",
                    "members_filter",
                    "wikipedia_tags_filter",
                    "organization_tags_filter",
                    "permissions",
                ),
                "split": ("blog_entries",),
            },
        ),
    }
    settings = {
        "searchableAttributes": [
            "id",
            "title",
            "purpose",
            "description",
            "blog_entries",
            "members",
            "categories",
            "wikipedia_tags",
            "organization_tags",
            "organizations",
        ],
        "attributesForFaceting": [
            "organizations",
            "filterOnly(language)",
            "filterOnly(sdgs)",
            "filterOnly(categories_filter)",
            "filterOnly(members_filter)",
            "filterOnly(wikipedia_tags_filter)",
            "filterOnly(organization_tags_filter)",
            "filterOnly(permissions)",
        ],
        "paginationLimitedTo": 5000,
        "hitsPerPage": 10,
        "attributeForDistinct": "id",
        "attributesToRetrieve": ["objectID", "id"],
        "attributesToHighlight": [],
        "separatorsToIndex": "#.%&~£¥$§€<>@-_*",
        # see https://www.algolia.com/doc/api-reference/api-parameters/separatorsToIndex/
        "indexLanguages": settings.REQUIRED_LANGUAGES,
    }

    def should_index(self, project: Project) -> bool:
        """Only index not soft-deleted project."""
        return project.deleted_at is None

    def get_indexing_queryset(self) -> QuerySet:
        """Prefetch relations to speed-up indexing."""
        return self.model.objects.filter(deleted_at=None).prefetch_related(
            "categories",
            "wikipedia_tags",
            "organization_tags",
            "blog_entries",
            "organizations",
        )

    def prepare_members(self, project: Project) -> List[str]:
        """Return the members' names for Algolia indexing."""
        return [
            f"{member.given_name} {member.family_name}"
            for member in project.get_all_members()
        ]

    def prepare_categories(self, project: Project) -> List[str]:
        """Return the categories' name for Algolia indexing."""
        return [category.name for category in project.categories.all()]

    def prepare_wikipedia_tags(self, project: Project) -> List[str]:
        """Return the wikipedia tags' names for Algolia indexing."""
        return [wikipedia_tag.name for wikipedia_tag in project.wikipedia_tags.all()]

    def prepare_organization_tags(self, project: Project) -> List[str]:
        """Return the organization tags' names for Algolia indexing."""
        return [
            organization_tag.name
            for organization_tag in project.organization_tags.all()
        ]

    def prepare_organizations(self, project: Project) -> List[str]:
        """Return the organizations' code for Algolia indexing."""
        return [org.code for org in project.organizations.all()]

    def split_description(self, project: Project) -> Collection[str]:  # type: ignore
        """Split description every `TEXT_THRESHOLD` bytes.

        HTML is stripped since it can take up a lot of space, and it is
        irrelevant to the search.
        """
        description = strip_tags(project.description)

        if len(description) <= TEXT_THRESHOLD:
            yield description
            return

        for i in range(0, len(description), TEXT_THRESHOLD):
            yield description[i : i + TEXT_THRESHOLD]

    def split_blog_entries(self, project: Project) -> Collection[str]:  # type: ignore
        """Concatenate then split blog entries every `TEXT_THRESHOLD` bytes.

        HTML is stripped since it can take up a lot of space, and it is
        irrelevant to the search.
        """
        qs = project.blog_entries.iterator(64)
        buffer = ""
        try:
            while True:
                # Fill buffer
                while len(buffer) < 2**17:  # ~131 KB
                    entry = next(qs)
                    buffer += f"\n\n{entry.title}\n{strip_tags(entry.content)}"

                # Consume buffer to create splits
                for i in range(0, len(buffer), TEXT_THRESHOLD):
                    # If it would not fill a record, better fill the buffer to
                    # avoid creating small records
                    if len(buffer) - i < TEXT_THRESHOLD:
                        buffer = buffer[i:]
                        break

                    yield buffer[i : i + TEXT_THRESHOLD]
                # If somehow the buffer was exactly a multiple of TEXT_THRESHOLD
                else:
                    buffer = ""

        except StopIteration:
            # Consume remaining buffer, if any
            for i in range(0, len(buffer), TEXT_THRESHOLD):
                yield buffer[i : i + TEXT_THRESHOLD]

    def prepare_categories_filter(self, project: Project) -> List[str]:
        """Return the wikipedia tags' names for Algolia indexing."""
        return list(project.categories.all().values_list("id", flat=True))

    def prepare_wikipedia_tags_filter(self, project: Project) -> List[str]:
        """Return the wikipedia tags' names for Algolia indexing."""
        return list(
            project.wikipedia_tags.all().values_list("wikipedia_qid", flat=True)
        )

    def prepare_organization_tags_filter(self, project: Project) -> List[str]:
        """Return the organization tags' names for Algolia indexing."""
        return list(project.organization_tags.all().values_list("id", flat=True))

    def prepare_members_filter(self, project: Project) -> List[str]:
        """Return the members' names for Algolia indexing."""
        return list(project.get_all_members().values_list("id", flat=True))

    def prepare_permissions(self, project: Project) -> List[str]:
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


@register(ProjectUser)
class UserIndex(AlgoliaSplittingIndex):
    """Algolia index definition for `ProjectUser`."""

    index_name = "user"
    fields = {
        "unique": (
            "id",
            "email",
            "given_name",
            "family_name",
            "job",
            "personal_email",
            "sdgs",
            "organizations",
            "skills",
            "skills_filter",
            "permissions",
            "people_groups",
            "projects",
        ),
        "multiple": (
            {
                "id_suffix": "desc",
                "commons": (  # IDs and attributes for faceting
                    "id",
                    "organizations",
                    "sdgs",
                    "skills_filter",
                    "permissions",
                ),
                "split": ("description",),
            },
        ),
    }
    settings = {
        "searchableAttributes": [
            "id",
            "email",
            "given_name",
            "family_name",
            "job",
            "personal_email",
            "description",
            "skills",
            "people_groups",
            "projects",
        ],
        "attributesForFaceting": [
            "filterOnly(organizations)",
            "filterOnly(sdgs)",
            "filterOnly(skills_filter)",
            "filterOnly(permissions)",
        ],
        "paginationLimitedTo": 5000,
        "hitsPerPage": 10,
        "attributeForDistinct": "id",
        "attributesToRetrieve": ["objectID", "id"],
        "attributesToHighlight": [],
        "separatorsToIndex": "#.%&~£¥$§€<>@-_*",
        # see https://www.algolia.com/doc/api-reference/api-parameters/separatorsToIndex/
        "indexLanguages": settings.REQUIRED_LANGUAGES,
    }

    def prepare_skills(self, user: ProjectUser) -> List[str]:
        """Return the skills' names for Algolia indexing."""
        return [skill.wikipedia_tag.name for skill in user.skills.all()]

    def prepare_skills_filter(self, user: ProjectUser) -> List[str]:
        """Return the skills' qids for Algolia filtering."""
        return [skill.wikipedia_tag.wikipedia_qid for skill in user.skills.all()]

    def prepare_organizations(self, user: ProjectUser) -> List[str]:
        """Return the organizations' code for Algolia indexing."""
        return [org.code for org in user.get_related_organizations()]

    def prepare_permissions(self, user: ProjectUser) -> List[str]:
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

    def prepare_people_groups(self, user: ProjectUser) -> List[str]:
        """Return the people groups' names for Algolia indexing."""
        return [
            people_group.name
            for people_group in PeopleGroup.objects.filter(
                groups__users=user
            ).distinct()
        ]

    def prepare_projects(self, user: ProjectUser) -> List[str]:
        """Return the projects' names for Algolia indexing."""
        return [
            project.title
            for project in Project.objects.filter(groups__users=user).distinct()
        ]

    def split_description(self, user: ProjectUser) -> Collection[str]:  # type: ignore
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


@register(PeopleGroup)
class PeopleGroupIndex(AlgoliaSplittingIndex):
    """Algolia index definition for `PeopleGroup`."""

    index_name = "group"
    fields = {
        "unique": (
            "id",
            "name",
            "email",
            "organization",
            "permissions",
            "sdgs",
        ),
        "multiple": (
            {
                "id_suffix": "desc",
                "commons": (  # IDs and attributes for faceting
                    "id",
                    "organization",
                    "permissions",
                    "sdgs",
                ),
                "split": ("description",),
            },
        ),
    }
    settings = {
        "searchableAttributes": [
            "name",
            "email",
            "organization",
            "description",
        ],
        "attributesForFaceting": [
            "organization",
            "filterOnly(permissions)",
            "filterOnly(sdgs)",
        ],
        "paginationLimitedTo": 5000,
        "hitsPerPage": 10,
        "attributeForDistinct": "id",
        "attributesToRetrieve": ["objectID", "id"],
        "attributesToHighlight": [],
        "separatorsToIndex": "#.%&~£¥$§€<>@-_*",
        # see https://www.algolia.com/doc/api-reference/api-parameters/separatorsToIndex/
        "indexLanguages": settings.REQUIRED_LANGUAGES,
    }

    def prepare_organization(self, group: PeopleGroup) -> List[str]:
        """Return the organizations' code for Algolia indexing."""
        return group.organization.code if group.organization else None

    def split_description(self, group: PeopleGroup) -> Collection[str]:  # type: ignore
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

    def prepare_permissions(self, group: PeopleGroup) -> List[str]:
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
