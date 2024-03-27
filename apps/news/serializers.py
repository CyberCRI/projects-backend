from rest_framework import serializers

from apps.accounts.models import PeopleGroup
from apps.commons.serializers import OrganizationRelatedSerializer
from apps.files.models import Image
from apps.files.serializers import ImageSerializer
from apps.news.models import News
from apps.organizations.models import Organization


class NewsSerializer(OrganizationRelatedSerializer, serializers.ModelSerializer):
    header_image = ImageSerializer(read_only=True)
    organization = serializers.SlugRelatedField(
        slug_field="code", queryset=Organization.objects.all()
    )
    people_groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=PeopleGroup.objects.all()
    )

    # write_only
    header_image_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Image.objects.all(),
        source="header_image",
        required=False,
    )

    class Meta:
        model = News
        fields = [
            "id",
            "title",
            "content",
            "publication_date",
            "header_image",
            "organization",
            "people_groups",
            "language",
            "created_at",
            "updated_at",
            # write_only
            "header_image_id",
        ]

    def validate_people_groups(self, value):
        for group in value:
            if group.organization.code != self.context.get("organization_code"):
                # TODO : write a custom exception
                raise "PeopleGroupOrganizationError"
        return value

    def validate_organization(self, value):
        if self.instance and value != self.instance.organization:
            # TODO : write a custom exception
            raise "InvitationOrganizationChangeError"
        return value
