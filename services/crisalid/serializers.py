from rest_framework import serializers

from apps.accounts.models import ProjectUser
from services.crisalid.models import Document, Identifier, Researcher


class ProjectUserMinimalSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUser
        fields = ("id", "display_name", "slug")

    def get_display_name(self, instance: ProjectUser) -> str:
        return str(instance)


class IdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Identifier
        fields = "__all__"


class ResearcherSerializerLight(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        fields = ("id", "display_name", "documents")

    def get_documents(self, instance):
        return instance.documents.group_count()


class ResearcherSerializer(serializers.ModelSerializer):
    user = ProjectUserMinimalSerializer()
    identifiers = IdentifierSerializer(many=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        exclude = ("crisalid_uid",)

    def get_display_name(self, instance):
        return str(instance)


class ResearcherDocumentsSerializer(ResearcherSerializer):
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


class DocumentSerializer(serializers.ModelSerializer):
    contributors = ResearcherDocumentsSerializer(many=True)
    identifiers = IdentifierSerializer(many=True)

    class Meta:
        model = Document
        exclude = ("crisalid_uid",)


class DocumentAnalyticsSerializer(serializers.Serializer):
    roles = serializers.DictField(child=serializers.IntegerField())
    years = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField())
    )
    document_types = serializers.DictField(child=serializers.IntegerField())
