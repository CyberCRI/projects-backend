from rest_framework import serializers

from apps.accounts.models import ProjectUser
from apps.commons.fields import PrivacySettingProtectedMethodField
from apps.commons.serializers import PrivacySerializer
from apps.modules.serializers import ModulesSerializers
from services.crisalid.models import Document, Identifier, Researcher
from services.translator.serializers import auto_translated


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


class ResearcherSerializer(PrivacySerializer, serializers.ModelSerializer):
    user = ProjectUserMinimalSerializer()
    # TODO(remi): change privacy field for identifiers (not based in socials)
    identifiers = PrivacySettingProtectedMethodField(privacy_field="socials")

    class Meta:
        model = Researcher
        fields = ("id", "display_name", "identifiers", "user")

    def get_identifiers(self, instance):
        """remove privacy identifiers (eppn/local)"""
        identifiers = []
        for identifier in instance.identifiers.all():
            if identifier.harvester in Researcher.PRIVACY_HARVESTER:
                continue
            identifiers.append(identifier)
        return IdentifierSerializer(identifiers, many=True).data


class ResearcherSerializerLight(ResearcherSerializer):
    class Meta(ResearcherSerializer.Meta):
        fields = ("id", "display_name", "identifiers")


class ResearcherDocumentsSerializer(ResearcherSerializer):
    class Meta(ResearcherSerializer.Meta):
        fields = ("id", "user", "display_name")


@auto_translated
class DocumentSerializer(ModulesSerializers, serializers.ModelSerializer):
    contributors = ResearcherDocumentsSerializer(many=True)
    identifiers = IdentifierSerializer(many=True)

    class Meta:
        model = Document
        exclude = ("updated",)


class DocumentLightSerializer(DocumentSerializer):
    class Meta(DocumentSerializer.Meta):
        fields = ("title", "publication_date", "document_type", "modules")
        modules_keys = ()


class DocumentAnalyticsSerializer(serializers.Serializer):
    roles = serializers.DictField(child=serializers.IntegerField())
    years = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField())
    )
    document_types = serializers.DictField(child=serializers.IntegerField())
