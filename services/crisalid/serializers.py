from rest_framework import serializers

from apps.accounts.models import ProjectUser
from apps.commons.fields import PrivacySettingProtectedMethodField
from apps.commons.serializers import PrivacySerializer
from apps.modules.serializers import ModulesSerializers
from apps.skills.serializers import TagSerializer
from services.crisalid.models import (
    Document,
    DocumentDomains,
    Identifier,
    Journal,
    Patent,
    Researcher,
    ResearcherDomains,
)
from services.crisalid.models.document import DocumentJournal
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


class ResearcherDomainsSerializer(serializers.ModelSerializer):
    domain = TagSerializer()

    class Meta:
        model = ResearcherDomains
        fields = (
            "domain",
            "level",
        )


@auto_translated
class ResearcherSerializer(
    ModulesSerializers, PrivacySerializer, serializers.ModelSerializer
):
    user = ProjectUserMinimalSerializer()
    # TODO(remi): change privacy field for identifiers (not based in socials)
    identifiers = PrivacySettingProtectedMethodField(privacy_field="socials")

    domains = ResearcherDomainsSerializer(source="researcher_domains", many=True)

    class Meta:
        model = Researcher
        fields = (
            "id",
            "display_name",
            "identifiers",
            "user",
            "bio",
            "short_bio",
            "h_index",
            "i10_index",
            "domains",
            "modules",
        )

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
        fields = (
            "id",
            "display_name",
            "identifiers",
            "bio",
            "short_bio",
            "h_index",
            "i10_index",
            "domains",
            "modules",
        )


class ResearcherDocumentsSerializer(ResearcherSerializer):
    class Meta(ResearcherSerializer.Meta):
        fields = ("id", "user", "display_name")


class DocumentDomainsSerializer(serializers.ModelSerializer):
    domains = ResearcherDomainsSerializer(source="document_domains", many=True)

    class Meta:
        model = DocumentDomains
        fields = ("id", "level", "domain")


@auto_translated
class DocumentSerializer(ModulesSerializers, serializers.ModelSerializer):
    contributors = ResearcherDocumentsSerializer(many=True)
    identifiers = IdentifierSerializer(many=True)

    class Meta:
        model = Document
        exclude = ("updated_at", "created_at", "journals")


class DocumentLightSerializer(DocumentSerializer):
    class Meta(DocumentSerializer.Meta):
        fields = ("id", "title", "publication_date", "document_type", "modules")
        exclude = None
        modules_keys = ()


class DocumentAnalyticsSerializer(serializers.Serializer):
    roles = serializers.DictField(child=serializers.IntegerField())
    years = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField())
    )
    document_types = serializers.DictField(child=serializers.IntegerField())


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = ("id", "title", "acronym")


class CitationSerializer(serializers.ModelSerializer):
    document = DocumentLightSerializer()
    journal = JournalSerializer()

    class Meta:
        model = DocumentJournal
        fields = ("document", "journal")


@auto_translated
class PatentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patent
        fields = (
            "id",
            "name",
            "description",
            "date",
            "link",
        )
