from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action

from apps.accounts.models import ProjectUser, Skill, PrivacySettings
from apps.accounts.serializers import UserLightSerializer
from apps.commons.permissions import ReadOnly
from apps.commons.views import MultipleIDViewsetMixin, PaginatedViewSet
from apps.misc.models import WikipediaTag
from apps.misc.serializers import WikipediaTagSerializer
from apps.organizations.models import Organization


class OrganizationMentorshipViewset(PaginatedViewSet):
    serializer_class = WikipediaTagSerializer
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
            if request_user.is_superuser or request_user in (organization.admins.all() | organization.facilitators.all()):
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
        wikipedia_tags = (
            WikipediaTag.objects.filter(skills__in=skills)
            .annotate(
                mentors_count=Count(
                    "skills__user", filter=Q(skills__can_mentor=True), distinct=True
                )
            )
            .order_by("-mentors_count")
            .distinct()
        )
        return self.get_paginated_list(wikipedia_tags)

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
        wikipedia_tags = (
            WikipediaTag.objects.filter(skills__in=skills)
            .annotate(
                mentorees_count=Count(
                    "skills__user", filter=Q(skills__needs_mentor=True), distinct=True
                )
            )
            .order_by("-mentorees_count")
            .distinct()
        )
        return self.get_paginated_list(wikipedia_tags)


class UserMentorshipViewset(PaginatedViewSet, MultipleIDViewsetMixin):
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
            if request_user.is_superuser or request_user in (organization.admins.all() | organization.facilitators.all()):
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
        user = get_object_or_404(self.request.user.get_user_queryset(), id=self.kwargs["user_id"])
        user_mentored_skills = WikipediaTag.objects.filter(
            user=user,
            skills__can_mentor=True,
        ).distinct()
        mentorees_skills = Skill.objects.filter(
            user__in=self.get_user_queryset(),
            needs_mentor=True,
            wikipedia_tag__in=user_mentored_skills,
        ).distinct()
        users = ProjectUser.objects.filter(skills__in=mentorees_skills).annotate(
            needs_mentoring_on=ArrayAgg(
                "skills",
                filter=Q(
                    skills__needs_mentor=True,
                    skills__wikipedia_tag__in=user_mentored_skills,
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
        user = get_object_or_404(self.request.user.get_user_queryset(), id=self.kwargs["user_id"])
        user_mentoree_skills = WikipediaTag.objects.filter(
            skills__user=user,
            skills__needs_mentor=True,
        ).distinct()
        mentors_skills = Skill.objects.filter(
            user__in=self.get_user_queryset(),
            can_mentor=True,
            wikipedia_tag__in=user_mentoree_skills,
        ).distinct()
        users = ProjectUser.objects.filter(skills__in=mentors_skills).annotate(
            can_mentor_on=ArrayAgg(
                "skills",
                filter=Q(
                    skills__can_mentor=True,
                    skills__wikipedia_tag__in=user_mentoree_skills,
                ),
                distinct=True,
            )
        )
        return self.get_paginated_list(users)
