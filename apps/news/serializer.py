from rest_framework import serializers

from apps.accounts.models import PeopleGroup
from apps.commons.serializers import OrganizationRelatedSerializer
from apps.files.models import Image
from apps.files.serializers import ImageSerializer
from apps.news.models import News
from apps.organizations.serializers import OrganizationSerializer


class NewsSerializer(OrganizationRelatedSerializer, serializers.ModelSerializer):
    header_image = ImageSerializer(read_only=True)
    organizations = OrganizationSerializer(many=True, read_only=True)
    people_groups = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=PeopleGroup.objects.all()
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
            "organizations",
            "people_groups",
            "language",
            "created_at",
            "updated_at",
            # write_only
            "header_image_id",
        ]
