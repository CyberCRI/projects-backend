import datetime
from typing import Any

from django.db import models
from rest_framework import serializers

from apps.accounts.models import PeopleGroup, PeopleGroupLocation, ProjectUser
from apps.announcements.models import Announcement
from apps.commons.mixins import OrganizationRelated
from apps.feedbacks.models import Comment, Follow, Review
from apps.files.models import AttachmentFile, AttachmentLink
from apps.files.serializers import ImageSerializer
from apps.newsfeed.models import Event, Instruction, News
from apps.organizations.models import Organization
from apps.projects.models import (
    BlogEntry,
    Goal,
    Location,
    Project,
    ProjectMessage,
    ProjectTab,
)
from apps.skills.models import Skill, Tag
from apps.skills.serializers import TagSerializer
from services.crisalid.models import Document, DocumentTypeCentralized
from services.translator.serializers import external_auto_translated


class StatsOrganizationSerializer(serializers.ModelSerializer):
    logo_image = ImageSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    project_count = serializers.IntegerField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "background_color",
            "code",
            "language",
            "name",
            "website_url",
            "created_at",
            "updated_at",
            "logo_image",
            "tags",
            "project_count",
        ]


class ProjectBySDG(serializers.Serializer):
    sdg = serializers.IntegerField()
    project_count = serializers.IntegerField()


class ProjectByMonth(serializers.Serializer):
    month = serializers.DateField()
    created_count = serializers.IntegerField()
    updated_count = serializers.IntegerField()


@external_auto_translated
class TagProjectSerializer(serializers.ModelSerializer):
    projects = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Project.objects.all()
    )
    project_count = serializers.IntegerField()

    class Meta:
        model = Tag
        fields = ["id", "title", "projects", "project_count"]


class StatsSerializer(serializers.Serializer):
    by_sdg = ProjectBySDG(many=True)
    by_month = ProjectByMonth(many=True)
    top_tags = TagProjectSerializer(many=True)
    total = serializers.IntegerField()


class OrganizationsAnalyticsField(serializers.Field):
    """
    Base class for fields computed from `OrganizationRelated` models.

    The values of all organizations are computed at once on the first call to
    `to_representation`, so a list of organizations costs a few queries instead
    of a few queries per organization.
    """

    @staticmethod
    def check_organization_related(model: type[models.Model]):
        if not issubclass(model, OrganizationRelated):
            raise TypeError(
                f"{model.__name__} must be a subclass of OrganizationRelated."
            )

    @classmethod
    def aggregate_by_organization(
        cls, queryset: models.QuerySet, aggregate: models.Aggregate
    ) -> dict[int, Any]:
        """
        Compute `aggregate` for all organizations in a single query, and return it
        as an `{organization_id: value}` dict. Organizations without any instance
        are missing from the result.
        """
        cls.check_organization_related(queryset.model)
        lookup = queryset.model.organization_query_string
        return dict(
            queryset.filter(**{f"{lookup}__isnull": False})
            .order_by()
            .values_list(lookup)
            .annotate(value=aggregate)
        )

    def bind(self, field_name: str, parent: serializers.Serializer):
        super().bind(field_name, parent)
        self._values = None

    def get_values(self) -> dict[int, Any]:
        """Return an `{organization_id: value}` dict for all organizations."""
        raise NotImplementedError()

    def get_value_for(self, organization: Organization) -> Any:
        if self._values is None:
            self._values = self.get_values()
        return self._values.get(organization.pk)


class OrganizationRelatedCountField(
    OrganizationsAnalyticsField, serializers.IntegerField
):
    """
    Count the instances of an `OrganizationRelated` model linked to the serialized
    organization.

    If `date_field` is given, only instances where this field is between the
    `from_date` and `to_date` (both included) of the serializer context are
    counted. `to_date` is optional.
    """

    def __init__(
        self,
        model: type[models.Model],
        date_field: str | None = None,
        **filters,
    ):
        self.check_organization_related(model)
        self.model = model
        self.date_field = date_field
        self.filters = filters
        super().__init__(source="*", read_only=True)

    def get_values(self) -> dict[int, int]:
        queryset = self.model.objects.filter(**self.filters)
        if self.date_field:
            queryset = queryset.filter(
                **{f"{self.date_field}__date__gte": self.context["from_date"]}
            )
            to_date = self.context.get("to_date")
            if to_date:
                queryset = queryset.filter(**{f"{self.date_field}__date__lte": to_date})
        return self.aggregate_by_organization(
            queryset, models.Count("pk", distinct=True)
        )

    def to_representation(self, organization: Organization) -> int:
        return self.get_value_for(organization) or 0


class OrganizationRelatedLastDateField(
    OrganizationsAnalyticsField, serializers.DateTimeField
):
    """
    Return the most recent value of `date_field` among the instances of the given
    `OrganizationRelated` models linked to the serialized organization.

    Return `None` if there is no such instance. The `from_date` and `to_date` of
    the serializer context are ignored.
    """

    def __init__(self, date_field: str, *model_classes: type[models.Model]):
        for model in model_classes:
            self.check_organization_related(model)
        self.date_field = date_field
        self.model_classes = model_classes
        super().__init__(source="*", read_only=True, allow_null=True)

    def get_values(self) -> dict[int, datetime.datetime]:
        values = {}
        for model in self.model_classes:
            dates = self.aggregate_by_organization(
                model.objects.all(), models.Max(self.date_field)
            )
            for organization_id, date in dates.items():
                if date and (
                    organization_id not in values or date > values[organization_id]
                ):
                    values[organization_id] = date
        return values

    def to_representation(self, organization: Organization) -> str | None:
        date = self.get_value_for(organization)
        return super().to_representation(date) if date else None


class GlobalAnalyticsSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source="website_url", read_only=True)
    last_update = OrganizationRelatedLastDateField(
        "updated_at", Project, News, PeopleGroup, Event, Instruction
    )
    last_login = OrganizationRelatedLastDateField("last_login", ProjectUser)
    projects = OrganizationRelatedCountField(Project)
    projects_created_period = OrganizationRelatedCountField(Project, "created_at")
    projects_updated_period = OrganizationRelatedCountField(Project, "updated_at")
    users = OrganizationRelatedCountField(ProjectUser)
    users_created_period = OrganizationRelatedCountField(ProjectUser, "created_at")
    users_logged_in_period = OrganizationRelatedCountField(ProjectUser, "last_login")
    groups = OrganizationRelatedCountField(PeopleGroup)
    groups_created_period = OrganizationRelatedCountField(PeopleGroup, "created_at")
    groups_updated_period = OrganizationRelatedCountField(PeopleGroup, "updated_at")
    news = OrganizationRelatedCountField(News)
    news_created_period = OrganizationRelatedCountField(News, "created_at")
    news_updated_period = OrganizationRelatedCountField(News, "updated_at")
    events = OrganizationRelatedCountField(Event)
    events_created_period = OrganizationRelatedCountField(Event, "created_at")
    events_updated_period = OrganizationRelatedCountField(Event, "updated_at")
    instructions = OrganizationRelatedCountField(Instruction)
    instructions_created_period = OrganizationRelatedCountField(
        Instruction, "created_at"
    )
    instructions_updated_period = OrganizationRelatedCountField(
        Instruction, "updated_at"
    )
    user_skills = OrganizationRelatedCountField(Skill)
    group_locations = OrganizationRelatedCountField(PeopleGroupLocation)
    group_publications = OrganizationRelatedCountField(
        Document, document_type__in=DocumentTypeCentralized.publications
    )
    group_conferences = OrganizationRelatedCountField(
        Document, document_type__in=DocumentTypeCentralized.conferences
    )
    project_announcements = OrganizationRelatedCountField(Announcement)
    project_comments = OrganizationRelatedCountField(Comment)
    project_follows = OrganizationRelatedCountField(Follow)
    project_reviews = OrganizationRelatedCountField(Review)
    project_messages = OrganizationRelatedCountField(ProjectMessage)
    project_tabs = OrganizationRelatedCountField(ProjectTab)
    project_goals = OrganizationRelatedCountField(Goal)
    project_locations = OrganizationRelatedCountField(Location)
    project_blog_entries = OrganizationRelatedCountField(BlogEntry)
    project_files = OrganizationRelatedCountField(AttachmentFile)
    project_links = OrganizationRelatedCountField(AttachmentLink)

    class Meta:
        model = Organization
        fields = [
            "id",
            "code",
            "url",
            "created_at",
            "last_update",
            "last_login",
            "projects",
            "projects_created_period",
            "projects_updated_period",
            "users",
            "users_created_period",
            "users_logged_in_period",
            "groups",
            "groups_created_period",
            "groups_updated_period",
            "news",
            "news_created_period",
            "news_updated_period",
            "events",
            "events_created_period",
            "events_updated_period",
            "instructions",
            "instructions_created_period",
            "instructions_updated_period",
            "user_skills",
            "group_locations",
            "group_publications",
            "group_conferences",
            "project_announcements",
            "project_comments",
            "project_follows",
            "project_reviews",
            "project_messages",
            "project_tabs",
            "project_goals",
            "project_locations",
            "project_blog_entries",
            "project_files",
            "project_links",
        ]
