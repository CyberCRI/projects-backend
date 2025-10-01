from rest_framework import serializers

from apps.accounts.models import ProjectUser
from services.crisalid.models import Document, DocumentSource, Identifier, Researcher


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
    documents_count = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        fields = ("id", "display_name", "documents_count")

    def get_documents_count(self, instance):
        return instance.documents.count()


class ResearcherSerializer(serializers.ModelSerializer):
    user = ProjectUserMinimalSerializer()
    identifiers = IdentifierSerializer(many=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        exclude = ("crisalid_uid",)

    def get_display_name(self, instance):
        return str(instance)


class DocumentSourceSerializer(serializers.ModelSerializer):
    identifier = IdentifierSerializer()

    class Meta:
        model = DocumentSource
        fields = (
            "document_type",
            "value",
            "identifier",
        )


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
    # avoid circular import
    authors = ResearcherDocumentsSerializer(many=True)
    sources = DocumentSourceSerializer(many=True)

    class Meta:
        model = Document
        exclude = ("crisalid_uid",)
