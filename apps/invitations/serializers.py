from rest_framework import serializers

from apps.accounts.models import PeopleGroup
from apps.accounts.serializers import PeopleGroupLightSerializer, UserLightSerializer
from apps.commons.serializers.abc import OrganizationRelatedSerializer
from apps.commons.serializers.fields import HiddenSlugRelatedField
from apps.organizations.models import Organization

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
            raise serializers.ValidationError(
                "People group must belong to the invitation's organization."
            )
        return value

    def get_related_organizations(self):
        return Organization.objects.filter(code=self.context.get("organization_code"))

    def update(self, instance, validated_data):
        if "organization" in validated_data:
            raise serializers.ValidationError(
                "Cannot change the organization of an invitation."
            )
        return super().update(instance, validated_data)
