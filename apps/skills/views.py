from typing import Union

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import PrivacySettings, ProjectUser
from apps.accounts.permissions import HasBasePermission
from apps.accounts.serializers import UserLightSerializer
from apps.commons.filters import UnaccentSearchFilter
from apps.commons.permissions import IsOwner, ReadOnly, WillBeOwner
from apps.commons.utils import map_action_to_permission
from apps.commons.views import (
    MultipleIDViewsetMixin,
    PaginatedViewSet,
    ReadDestroyModelViewSet,
    WriteOnlyModelViewSet,
)
from apps.emailing.utils import render_message, send_email
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from services.wikipedia.interface import WikipediaService

from .exceptions import (
    DuplicatedMentoringError,
    MentoringCreatorStatusChangeError,
    SkillAlreadyAddedError,
    UserCannotMentorError,
    UserDoesNotNeedMentorError,
    UserIDIsNotProvidedError,
    WikipediaTagSearchLimitError,
)
from .filters import TagFilter
from .models import Mentoring, Skill, Tag, TagClassification
from .pagination import WikipediaPagination
from .serializers import (
    MentoringContactSerializer,
    MentoringResponseSerializer,
    MentoringSerializer,
    SkillSerializer,
    TagClassificationAddTagsSerializer,
    TagClassificationRemoveTagsSerializer,
    TagClassificationSerializer,
    TagSerializer,
)
from .utils import (
    set_default_language_title_and_description,
    update_or_create_wikipedia_tags,
)


class SkillViewSet(MultipleIDViewsetMixin, WriteOnlyModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | WillBeOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]
    multiple_lookup_fields = [
        (ProjectUser, "user_id"),
    ]

    def get_queryset(self):
        if "user_id" in self.kwargs:
            return self.queryset.filter(user_id=self.kwargs["user_id"])
        return self.queryset.none()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            raise SkillAlreadyAddedError

    def perform_create(self, serializer):
        if "user_id" in self.kwargs:
            user = get_object_or_404(ProjectUser, id=self.kwargs["user_id"])
            serializer.save(user=user)
        else:
            raise UserIDIsNotProvidedError


class TagClassificationViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    permission_classes = [ReadOnly]
    serializer_class = TagClassificationSerializer
    lookup_field = "id"
    multiple_lookup_fields = [
        (TagClassification, "id"),
    ]

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "tagclassification")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "organizations")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        organization_code = self.kwargs.get("organization_code", None)
        if organization_code:
            organization = get_object_or_404(Organization, code=organization_code)
            context["current_organization"] = organization
        return context

    def get_queryset(self):
        organization_code = self.kwargs.get("organization_code", None)
        if organization_code:
            return (
                TagClassification.objects.filter(
                    Q(organization__code=organization_code) | Q(is_public=True)
                )
                .distinct()
                .select_related("organization")
            )
        return TagClassification.objects.none()

    def perform_create(self, serializer: TagClassificationSerializer):
        organization_code = self.kwargs.get("organization_code", None)
        if organization_code:
            organization = get_object_or_404(Organization, code=organization_code)
            serializer.save(
                organization=organization,
                type=TagClassification.TagClassificationType.CUSTOM,
            )

    @extend_schema(request=TagClassificationAddTagsSerializer, responses={204: None})
    @action(
        detail=True,
        methods=["POST"],
        url_path="add-tags",
        url_name="add-tags",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_tagclassification", "skills")
            | HasOrganizationPermission("change_tagclassification"),
        ],
    )
    def add_tags(self, request, *args, **kwargs):
        tag_classification = self.get_object()
        serializer = TagClassificationAddTagsSerializer(
            data={"tag_classification": tag_classification.pk, **request.data},
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=TagClassificationRemoveTagsSerializer, responses={204: None})
    @action(
        detail=True,
        methods=["POST"],
        url_path="remove-tags",
        url_name="remove-tags",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_tagclassification", "skills")
            | HasOrganizationPermission("change_tagclassification"),
        ],
    )
    def remove_tags(self, request, *args, **kwargs):
        tag_classification = self.get_object()
        serializer = TagClassificationRemoveTagsSerializer(
            data={"tag_classification": tag_classification.pk, **request.data},
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = TagSerializer
    search_fields = [
        *[f"title_{language}" for language in settings.REQUIRED_LANGUAGES],
        *[f"description_{language}" for language in settings.REQUIRED_LANGUAGES],
    ]
    filter_backends = (
        UnaccentSearchFilter,
        DjangoFilterBackend,
        OrderingFilter,
    )
    multiple_lookup_fields = [
        (TagClassification, "tag_classification_id"),
    ]

    def get_tag_classification_id_from_lookup_value(
        self, tag_classification_id: str
    ) -> Union[int, str]:
        """
        Override the default method to handle multiple lookup values to allow fetching
        all tags from the organization that are enabled for projects or skills by using
        the slugs `enabled-for-projects` and `enabled-for-skills`.
        """
        if tag_classification_id in TagClassification.ReservedSlugs.values:
            return tag_classification_id
        return TagClassification.get_main_id(tag_classification_id)

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "tag")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "organizations")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_enabled_tags(
        self, organization_code: str, enabled_for: str
    ) -> QuerySet[Tag]:
        """
        Get all tags from an organization that are enabled for projects or skills.

        If one of the enabled classifications is Wikipedia, the method will also
        perform a search in the Wikipedia database before returning the results.

        This will only happen if the `search` parameter is provided in the request,
        it allows to add new tags from Wikipedia to the organization when searching
        multiple classifications at once.
        """
        if enabled_for == TagClassification.ReservedSlugs.ENABLED_FOR_PROJECTS:
            classifications = TagClassification.objects.filter(
                enabled_organizations_projects__code=organization_code
            )
        elif enabled_for == TagClassification.ReservedSlugs.ENABLED_FOR_SKILLS:
            classifications = TagClassification.objects.filter(
                enabled_organizations_skills__code=organization_code
            )
        else:
            return Tag.objects.none()
        wikipedia = TagClassification.get_or_create_default_classification(
            classification_type=TagClassification.TagClassificationType.WIKIPEDIA
        )
        if wikipedia in classifications and self.request.query_params.get(
            "search", None
        ):
            self.wikipedia_search(self.request)
        return Tag.objects.filter(tag_classifications__in=classifications)

    def get_queryset(self):
        """
        This viewset can be used in three ways:
        - To get all custom tags from an organization
            When accessed with the `organization_code` parameter in the URL
        - To get all tags from a specific classification
            When accessed with the `organization_code` and `tag_classification_id`
            parameters in the URL
        - To get all tags from an organization that are enabled for projects or skills
            When accessed with the `organization_code` and `tag_classification_id`
            parameters in the URL and the `tag_classification_id` parameter is set
            to `enabled-for-projects` or `enabled-for-skills`
        """
        organization_code = self.kwargs.get("organization_code", None)
        tag_classification_id = self.kwargs.get("tag_classification_id", None)
        if organization_code and not tag_classification_id:
            return Tag.objects.filter(organization__code=organization_code)
        if organization_code and tag_classification_id:
            if tag_classification_id in TagClassification.ReservedSlugs.values:
                return self.get_enabled_tags(organization_code, tag_classification_id)
            return Tag.objects.filter(tag_classifications__id=tag_classification_id)
        return Tag.objects.all()

    def create(self, request, *args, **kwargs):
        data = set_default_language_title_and_description(request.data)
        self.request.data.update(data)
        request.data.update(data)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer: TagSerializer):
        """
        Add the organization to the tag
        """
        organization_code = self.kwargs.get("organization_code", None)
        tag_classification_id = self.kwargs.get("tag_classification_id", None)
        if organization_code:
            organization = get_object_or_404(Organization, code=organization_code)
            instance = serializer.save(
                organization=organization,
                type=Tag.TagType.CUSTOM,
                secondary_type=Tag.SecondaryTagType.TAG,
            )
            if tag_classification_id:
                classification = get_object_or_404(
                    TagClassification, id=tag_classification_id
                )
                classification.tags.add(instance)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        List all custom tags of an organization (if only `organization_code` is provided
        in the url), or all tags from a specific classification (if `organization_code`
        and `tag_classification_id` are provided in the url).

        Additionally, when using this endpoint with the `tag_classification_id`
        parameter, you can use the following values instead of slugs to retrieve
        specific tags classifications:

        - `enabled-for-projects`: Tags that are enabled for projects in the organization
        - `enabled-for-skills`: Tags that are enabled for skills in the organization
        """
        wikipedia = TagClassification.get_or_create_default_classification(
            classification_type=TagClassification.TagClassificationType.WIKIPEDIA
        )
        if (
            self.request.query_params.get("search", None)
            and self.kwargs.get("tag_classification_id", None)
            and self.kwargs["tag_classification_id"]
            not in TagClassification.ReservedSlugs.values
            and int(self.kwargs["tag_classification_id"]) == int(wikipedia.id)
        ):
            return self.wikipedia_search(request)
        return super().list(request, *args, **kwargs)

    def wikipedia_search(self, request: Request) -> Response:
        params = {
            "query": str(self.request.query_params.get("search", "")),
            "language": str(self.request.query_params.get("language", "en")),
            "limit": int(self.request.query_params.get("limit", 50)),
            "offset": int(self.request.query_params.get("offset", 0)),
        }
        if params["limit"] > 50:
            raise WikipediaTagSearchLimitError
        wikipedia_qids, next_items = WikipediaService.search(**params)
        queryset = update_or_create_wikipedia_tags(wikipedia_qids)
        count = next_items + len(queryset)
        paginator = WikipediaPagination(count=count)()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(page, many=True)
        return paginator.get_paginated_response(data=serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="search",
                description="Search for a specific page name in the Wikipedia database.",
                required=True,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results in response, default to 5.",
                required=False,
                type=int,
                many=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    @action(detail=False, methods=["GET"])
    def autocomplete(self, request, *args, **kwargs):
        """
        Autocomplete custom tags of an organization (if only `organization_code` is
        provided in the url), or all tags from a specific classification (if
        `organization_code` and `tag_classification_id` are provided in the url).

        Additionally, when using this endpoint with the `tag_classification_id`
        parameter, you can use the following values instead of slugs to look through
        specific tags classifications:

        - `enabled-for-projects`: Tags that are enabled for projects in the organization
        - `enabled-for-skills`: Tags that are enabled for skills in the organization
        """
        language = self.request.query_params.get("language", "en")
        limit = int(self.request.query_params.get("limit", 5))
        search = self.request.query_params.get("search", "")
        queryset = (
            self.get_queryset()
            .filter(
                Q(**{f"title_{language}__unaccent__istartswith": search})
                | Q(**{f"title_{language}__unaccent__icontains": f" {search}"})
            )
            .distinct()
            .annotate(
                usage=Count("skills", distinct=True)
                + Count("projects", distinct=True)
                + Count("default_organizations_projects", distinct=True)
                + Count("default_organizations_skills", distinct=True)
                + Count("project_categories", distinct=True)
            )
            .order_by("-usage")[:limit]
        )
        data = queryset.values_list(f"title_{language}", flat=True)
        return Response(data)


class ReadTagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    filterset_class = TagFilter
    queryset = Tag.objects.all()
    permission_classes = [ReadOnly]


class OrganizationMentorshipViewset(PaginatedViewSet):
    serializer_class = TagSerializer
    permission_classes = [ReadOnly]

    def get_organization(self) -> Organization:
        organization_code = self.kwargs["organization_code"]
        return get_object_or_404(Organization, code=organization_code)

    def get_user_queryset(self):
        organization = self.get_organization()
        request_user = self.request.user
        user_queryset = self.request.user.get_user_queryset().filter(
            id__in=organization.get_all_members().values_list("id", flat=True)
        )
        if request_user.is_authenticated:
            if request_user.is_superuser or request_user in (
                organization.admins.all() | organization.facilitators.all()
            ):
                return user_queryset
            if request_user in organization.get_all_members():
                return user_queryset.filter(
                    Q(
                        privacy_settings__skills__in=[
                            PrivacySettings.PrivacyChoices.ORGANIZATION,
                            PrivacySettings.PrivacyChoices.PUBLIC,
                        ]
                    )
                    | Q(id=request_user.id)
                )
        return user_queryset.filter(
            privacy_settings__skills=PrivacySettings.PrivacyChoices.PUBLIC
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                required=False,
                type=int,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="mentored-skill",
        url_name="mentored-skill",
        permission_classes=[ReadOnly],
    )
    def mentored_skill(self, request, *args, **kwargs):
        """
        Get all skills in current organization that have at least one mentor.
        """
        skills = Skill.objects.filter(
            user__in=self.get_user_queryset(), can_mentor=True
        ).distinct()
        tags = (
            Tag.objects.filter(skills__in=skills)
            .annotate(
                mentors_count=Count(
                    "skills__user", filter=Q(skills__can_mentor=True), distinct=True
                )
            )
            .order_by("-mentors_count")
            .distinct()
        )
        return self.get_paginated_list(tags)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                required=False,
                type=int,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="mentoree-skill",
        url_name="mentoree-skill",
        permission_classes=[ReadOnly],
    )
    def mentoree_skill(self, request, *args, **kwargs):
        """
        Get all skills in current organization that have at least one person who wants to be mentored.
        """
        skills = Skill.objects.filter(
            user__in=self.get_user_queryset(), needs_mentor=True
        ).distinct()
        tags = (
            Tag.objects.filter(skills__in=skills)
            .annotate(
                mentorees_count=Count(
                    "skills__user", filter=Q(skills__needs_mentor=True), distinct=True
                )
            )
            .order_by("-mentorees_count")
            .distinct()
        )
        return self.get_paginated_list(tags)


class UserMentorshipViewset(MultipleIDViewsetMixin, PaginatedViewSet):
    serializer_class = UserLightSerializer
    permission_classes = [ReadOnly]
    multiple_lookup_fields = [
        (ProjectUser, "user_id"),
    ]

    def get_organization(self):
        organization_code = self.kwargs["organization_code"]
        return get_object_or_404(Organization, code=organization_code)

    def get_user(self):
        organization = self.get_organization()
        user_id = self.kwargs["user_id"]
        return get_object_or_404(organization.get_all_members(), id=user_id)

    def get_user_queryset(self):
        organization = self.get_organization()
        request_user = self.request.user
        user_queryset = self.request.user.get_user_queryset().filter(
            id__in=organization.get_all_members().values_list("id", flat=True)
        )
        if request_user.is_authenticated:
            if request_user.is_superuser or request_user in (
                organization.admins.all() | organization.facilitators.all()
            ):
                return user_queryset
            if request_user in organization.get_all_members():
                return user_queryset.filter(
                    Q(
                        privacy_settings__skills__in=[
                            PrivacySettings.PrivacyChoices.ORGANIZATION,
                            PrivacySettings.PrivacyChoices.PUBLIC,
                        ]
                    )
                )
        return user_queryset.filter(
            privacy_settings__skills=PrivacySettings.PrivacyChoices.PUBLIC
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                required=False,
                type=int,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="mentoree-candidate",
        url_name="mentoree-candidate",
        permission_classes=[ReadOnly],
    )
    def mentoree_candidate(self, request, *args, **kwargs):
        """
        Get all users in current organization that have at least one skill that could be mentored by the user.
        """
        user = get_object_or_404(
            self.request.user.get_user_queryset(), id=self.kwargs["user_id"]
        )
        user_mentored_skills = Tag.objects.filter(
            skills__user=user,
            skills__can_mentor=True,
        ).distinct()
        mentorees_skills = Skill.objects.filter(
            user__in=self.get_user_queryset(),
            needs_mentor=True,
            tag__in=user_mentored_skills,
        ).distinct()
        users = ProjectUser.objects.filter(skills__in=mentorees_skills).annotate(
            needs_mentor_on=ArrayAgg(
                "skills",
                filter=Q(
                    skills__needs_mentor=True,
                    skills__tag__in=user_mentored_skills,
                ),
                distinct=True,
            )
        )
        return self.get_paginated_list(users)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                required=False,
                type=int,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="mentor-candidate",
        url_name="mentor-candidate",
        permission_classes=[ReadOnly],
    )
    def mentor_candidate(self, request, *args, **kwargs):
        """
        Get all users in current organization that have at least one skill that could be mentored by the user.
        """
        user = get_object_or_404(
            self.request.user.get_user_queryset(), id=self.kwargs["user_id"]
        )
        user_mentoree_skills = Tag.objects.filter(
            skills__user=user,
            skills__needs_mentor=True,
        ).distinct()
        mentors_skills = Skill.objects.filter(
            user__in=self.get_user_queryset(),
            can_mentor=True,
            tag__in=user_mentoree_skills,
        ).distinct()
        users = ProjectUser.objects.filter(skills__in=mentors_skills).annotate(
            can_mentor_on=ArrayAgg(
                "skills",
                filter=Q(
                    skills__can_mentor=True,
                    skills__tag__in=user_mentoree_skills,
                ),
                distinct=True,
            )
        )
        return self.get_paginated_list(users)


class MentoringViewSet(MultipleIDViewsetMixin, ReadDestroyModelViewSet):
    queryset = Mentoring.objects.all()
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = MentoringSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return self.queryset.filter(
                Q(mentoree=self.request.user) | Q(mentor=self.request.user)
            ).distinct()
        return self.queryset.none()

    def get_skill_name(self, skill: Skill, language: str):
        return getattr(skill.tag, f"title_{language}", skill.tag.title)

    def send_email(
        self, template_folder: str, receiver: ProjectUser, skill: Skill, **kwargs
    ):
        language = receiver.language
        kwargs = {
            "sender": self.request.user,
            "receiver": receiver,
            "skill": self.get_skill_name(skill, language),
            **kwargs,
        }
        subject, _ = render_message(f"{template_folder}/object", language, **kwargs)
        text, html = render_message(f"{template_folder}/mail", language, **kwargs)
        reply_to = kwargs["reply_to"]
        send_email(
            subject, text, [receiver.email], html_content=html, reply_to=[reply_to]
        )

    @extend_schema(
        request=MentoringContactSerializer,
        responses={status.HTTP_200_OK: MentoringSerializer},
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="contact-mentor/(?P<skill_id>[^/]+)",
        url_name="contact-mentor",
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic
    def contact_mentor(self, request, *args, **kwargs):
        skill = get_object_or_404(Skill, id=int(self.kwargs["skill_id"]))
        if not skill.can_mentor:
            raise UserCannotMentorError
        # Create the mentoring instance
        serializer = MentoringContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = Mentoring.objects.create(
                skill=skill,
                mentor=skill.user,
                mentoree=self.request.user,
                created_by=self.request.user,
            )
        except IntegrityError:
            raise DuplicatedMentoringError
        # Send the email
        self.send_email(
            "contact_mentor",
            skill.user,
            skill,
            instance=instance,
            **serializer.validated_data,
        )
        return Response(MentoringSerializer(instance).data)

    @extend_schema(
        request=MentoringContactSerializer,
        responses={status.HTTP_200_OK: MentoringSerializer},
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="contact-mentoree/(?P<skill_id>[^/]+)",
        url_name="contact-mentoree",
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic
    def contact_mentoree(self, request, *args, **kwargs):
        """
        Contact a mentoree for help.
        """
        skill = get_object_or_404(Skill, id=int(self.kwargs["skill_id"]))
        if not skill.needs_mentor:
            raise UserDoesNotNeedMentorError
        # Create the mentoring instance
        serializer = MentoringContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = Mentoring.objects.create(
                skill=skill,
                mentor=self.request.user,
                mentoree=skill.user,
                created_by=self.request.user,
            )
        except IntegrityError:
            raise DuplicatedMentoringError
        # Send the email
        self.send_email(
            "contact_mentoree",
            skill.user,
            skill,
            instance=instance,
            **serializer.validated_data,
        )
        return Response(MentoringSerializer(instance).data)

    @extend_schema(
        request=MentoringResponseSerializer,
        responses={status.HTTP_200_OK: MentoringSerializer},
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="respond",
        url_name="respond",
    )
    @transaction.atomic
    def respond(self, request, *args, **kwargs):
        """
        Reply to the mentoring request and update the Mentoring's status.
        An email with the user's message will be sent to the mentoring's initiator.

        The status can be:
            - pending : the mentoring is still being discussed
            - accepted : the mentoring is accepted
            - rejected : the mentoring is rejected
        """
        instance = self.get_object()
        if self.request.user == instance.created_by:
            # Only the receiver of the mentoring request can accept or reject it
            raise MentoringCreatorStatusChangeError
        # Update the mentoring status
        serializer = MentoringResponseSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.status = serializer.validated_data.pop("status")
        instance.save()
        # Send the email
        if instance.created_by == instance.mentor:
            template = f"mentoree_response_{instance.status}"
        elif instance.created_by == instance.mentoree:
            template = f"mentor_response_{instance.status}"
        else:
            # This part should never be reached
            return Response(status=status.HTTP_400_BAD_REQUEST)
        self.send_email(
            template,
            instance.created_by,
            instance.skill,
            instance=instance,
            **serializer.validated_data,
        )
        return Response(MentoringSerializer(instance).data)
