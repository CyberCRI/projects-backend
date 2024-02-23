from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.commons.serializers import TranslatedModelSerializer
from apps.organizations.models import Organization
from services.wikipedia.interface import WikipediaService

from .models import Tag, WikipediaTag


class WikipediaTagSerializer(TranslatedModelSerializer):
    class Meta:
        model = WikipediaTag
        fields = ["id", "name", "wikipedia_qid", "description"]
        lookup_field = "wikipedia_qid"


class TagSerializer(serializers.ModelSerializer):
    organization = serializers.SlugRelatedField(
        slug_field="code", queryset=Organization.objects.all()
    )

    class Meta:
        model = Tag
        fields = ["id", "name", "organization"]


@extend_schema_field(OpenApiTypes.STR)
class TagRelatedField(serializers.RelatedField):
    def get_queryset(self) -> QuerySet:
        return WikipediaTag.objects.all()

    def to_representation(self, instance: WikipediaTag) -> dict:
        return {"wikipedia_qid": instance.wikipedia_qid, "name": instance.name}

    def to_internal_value(self, qid: str) -> WikipediaTag:
        return WikipediaService.update_or_create_wikipedia_tag(qid)
