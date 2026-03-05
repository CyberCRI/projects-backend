from rest_framework import serializers

from apps.accounts.models import ProjectUser
from apps.commons.fields import PrivacySettingProtectedMethodField
from services.crisalid.models import Document, Identifier, Researcher
from services.translator.serializers import AutoTranslatedModelSerializer


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
        exclude = ("id",)


class ResearcherSerializerLight(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()
    identifiers = PrivacySettingProtectedMethodField(privacy_field="socials")

    class Meta:
        model = Researcher
        fields = ("id", "display_name", "documents", "identifiers")

    def get_documents(self, instance):
        return instance.documents.group_count()

    def get_identifiers(self, instance):
        """remove privacy identifiers (eppn/local)"""
        identifiers = []
        for identifier in instance.identifiers.all():
            if identifier.harvester in Researcher.PRIVACY_HARVESTER:
                continue
            identifiers.append(identifier)
        return IdentifierSerializer(identifiers, many=True).data


class ResearcherSerializer(serializers.ModelSerializer):
    user = ProjectUserMinimalSerializer()
    identifiers = IdentifierSerializer(many=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        fields = ("id", "user", "identifiers", "display_name")

    def get_display_name(self, instance):
        return str(instance)


class ResearcherDocumentsSerializer(ResearcherSerializer):
    user = ProjectUserMinimalSerializer()

    class Meta:
        model = Researcher
        fields = ("display_name", "user", "id")


class DocumentLightSerializer(AutoTranslatedModelSerializer):
    class Meta:
        model = Document
        fields = ("title", "publication_date", "document_type")


class DocumentSerializer(DocumentLightSerializer):
    contributors = ResearcherDocumentsSerializer(many=True)
    identifiers = IdentifierSerializer(many=True)
    similars = serializers.SerializerMethodField()

    class Meta:
        model = Document
        exclude = ("updated",)

    def get_similars(self, instance: Document):
        """return similar count"""
        return instance.similars().count()


class DocumentAnalyticsSerializer(serializers.Serializer):
    roles = serializers.DictField(child=serializers.IntegerField())
    years = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField())
    )
    document_types = serializers.DictField(child=serializers.IntegerField())
