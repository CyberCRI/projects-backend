from django.db.models import Q
from rest_framework import serializers

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.serializers import PeopleGroupLightSerializer, UserLightSerializer
from apps.commons.fields import HiddenSlugRelatedField, UserMultipleIdRelatedField
from apps.commons.serializers import OrganizationRelatedSerializer
from apps.invitations.models import AccessRequest
from apps.organizations.models import Organization

from .exceptions import (
    AccessRequestDisabledError,
    AccessRequestForEmailAlreadyExistsError,
    AccessRequestForUserAlreadyExistsError,
    AccessRequestUserAlreadyExistsError,
    AccessRequestUserAlreadyMemberError,
    InvitationOrganizationChangeError,
    InvitationPeopleGroupOrganizationError,
)
from .models import Invitation


class InvitationSerializer(OrganizationRelatedSerializer):
    owner = UserLightSerializer(read_only=True)
    organization = HiddenSlugRelatedField(
        slug_field="code", queryset=Organization.objects.all(), required=False
    )
    people_group = PeopleGroupLightSerializer(read_only=True)
    people_group_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=PeopleGroup.objects.all(), source="people_group"
    )

    class Meta:
        model = Invitation
        read_only_fields = ["token", "created_at", "people_group", "id", "owner"]
        fields = read_only_fields + [
            "organization",
            "people_group_id",
            "description",
            "expire_at",
        ]

    def validate_people_group_id(self, value):
        if not PeopleGroup.objects.filter(
            id=value.id, organization__code=self.context.get("organization_code")
        ).exists():
            raise InvitationPeopleGroupOrganizationError
        return value

    def validate_organization(self, value):
        if self.instance and value != self.instance.organization:
            raise InvitationOrganizationChangeError
        return value

    def get_related_organizations(self):
        return Organization.objects.filter(code=self.context.get("organization_code"))


class AccessRequestSerializer(serializers.ModelSerializer):
    organization = serializers.SlugRelatedField(
        slug_field="code", queryset=Organization.objects.all()
    )
    user = UserMultipleIdRelatedField(
        queryset=ProjectUser.objects.all(), allow_null=True
    )

    class Meta:
        model = AccessRequest
        read_only_fields = ["id", "created_at", "status"]
        fields = read_only_fields + [
            "organization",
            "user",
            "email",
            "given_name",
            "family_name",
            "job",
            "message",
        ]

    def validate_email(self, value: str) -> str:
        if self.initial_data.get("user"):
            return ""
        if ProjectUser.objects.filter(
            Q(email=value) | Q(personal_email=value)
        ).exists():
            raise AccessRequestUserAlreadyExistsError
        if AccessRequest.objects.filter(
            organization__code=self.initial_data.get("organization"),
            status=AccessRequest.Status.PENDING,
            email=value,
        ).exists():
            raise AccessRequestForEmailAlreadyExistsError
        return value

    def validate_given_name(self, value: str) -> str:
        if self.initial_data.get("user"):
            return ""
        return value

    def validate_family_name(self, value: str) -> str:
        if self.initial_data.get("user"):
            return ""
        return value

    def validate_job(self, value: str) -> str:
        if self.initial_data.get("user"):
            return ""
        return value

    def validate_user(self, value: ProjectUser) -> ProjectUser:
        if value:
            organization_code = self.initial_data.get("organization")
            if Organization.objects.filter(
                code=organization_code, groups__users=value
            ).exists():
                raise AccessRequestUserAlreadyMemberError
            if AccessRequest.objects.filter(
                organization__code=organization_code,
                status=AccessRequest.Status.PENDING,
                user=value,
            ).exists():
                raise AccessRequestForUserAlreadyExistsError
        return value

    def validate_organization(self, value: Organization) -> Organization:
        if not value.access_request_enabled:
            raise AccessRequestDisabledError
        return value

    def to_representation(self, instance):
        if instance.user:
            return {
                **super().to_representation(instance),
                "email": instance.user.email,
                "given_name": instance.user.given_name,
                "family_name": instance.user.family_name,
                "job": instance.user.job,
            }
        return super().to_representation(instance)


class AccessRequestManySerializer(serializers.Serializer):
    """Used to accept or decline several access requests at once."""

    access_requests = serializers.PrimaryKeyRelatedField(
        many=True, queryset=AccessRequest.objects.all()
    )

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class AccessRequestResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    message = serializers.CharField(allow_blank=True)


class ProcessAccessRequestSerializer(serializers.Serializer):
    success = serializers.ListField(
        child=AccessRequestResultSerializer(), required=False
    )
    error = serializers.ListField(child=AccessRequestResultSerializer(), required=False)
    warning = serializers.ListField(
        child=AccessRequestResultSerializer(), required=False
    )

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
