from rest_framework import serializers

from apps.accounts.models import ProjectUser
from services.crisalid.models import Identifier, Publication, Researcher


class ProjectUserMinimalSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUser
        fields = ("id", "display_name", "slug")

    def get_display_name(self, instance: ProjectUser) -> str:
        return instance.get_full_name()


class IdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Identifier
        fields = "__all__"


class ResearcherSerializerLight(serializers.ModelSerializer):
    publications_count = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        fields = ("id", "display_name", "publications_count")

    def get_publications_count(self, instance):
        return instance.publications.count()


class ResearcherSerializer(serializers.ModelSerializer):
    user = ProjectUserMinimalSerializer()
    identifiers = IdentifierSerializer(many=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        exclude = ("crisalid_uid",)

    def get_display_name(self, instance):
        return str(instance)


class ResearcherPublicationsSerializer(ResearcherSerializer):
    user = ProjectUserMinimalSerializer()
    identifiers = IdentifierSerializer(many=True)

    class Meta:
        model = Researcher
        fields = (
            "identifiers",
            "display_name",
            "user",
            "id",
        )


class PublicationSerializer(serializers.ModelSerializer):
    # avoid circular import
    authors = ResearcherPublicationsSerializer(many=True)
    identifiers = IdentifierSerializer(many=True)

    class Meta:
        model = Publication
        exclude = ("crisalid_uid",)
