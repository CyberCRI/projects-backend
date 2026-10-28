from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.fields import PrivacySettingProtectedMethodField
from apps.commons.serializers import PrivacySerializer
from apps.modules.serializers import ModulesSerializers
from apps.skills.models import Tag
from apps.skills.serializers import TagSerializer
from services.crisalid.models import (
    AuthorityOrganization,
    Award,
    Document,
    DocumentDomains,
    DocumentJournal,
    Identifier,
    Journal,
    Patent,
    Researcher,
    ResearcherDomains,
    ResearcherStructure,
    Structure,
    StructureRelation,
)
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


@auto_translated
class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Award
        fields = (
            "id",
            "name",
            "description",
            "date",
            "link",
        )
class StructurePeopleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeopleGroup
        fields = ("id", "slug", "name")


class StructureLightSerializer(serializers.ModelSerializer):
    people_group = StructurePeopleGroupSerializer(read_only=True)

    class Meta:
        model = Structure
        fields = (
            "id",
            "crisalid_uid",
            "name",
            "acronym",
            "generic_type",
            "national_type",
            "main_mission",
            "external",
            "people_group",
        )


class SupervisingInstitutionSerializer(serializers.ModelSerializer):
    structure = StructureLightSerializer(source="related_structure", read_only=True)

    class Meta:
        model = StructureRelation
        fields = ("position", "start_date", "end_date", "structure")


class StructureSerializer(ModulesSerializers, serializers.ModelSerializer):
    people_group = StructurePeopleGroupSerializer(read_only=True)
    supervising_institutions = serializers.SerializerMethodField()

    class Meta:
        model = Structure
        fields = (
            "id",
            "crisalid_uid",
            "name",
            "acronym",
            "description",
            "generic_type",
            "national_type",
            "main_mission",
            "external",
            "people_group",
            "supervising_institutions",
            "modules",
        )

    @extend_schema_field(SupervisingInstitutionSerializer(many=True))
    def get_supervising_institutions(self, instance: Structure) -> list[dict]:
        modules = instance.modules_by_user(
            self.context["request"].user, self.context.get("organization")
        )
        return SupervisingInstitutionSerializer(
            modules.supervising_institutions(), many=True
        ).data


class ResearchDomainSerializer(serializers.ModelSerializer):
    documents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = (
            "id",
            "type",
            "secondary_type",
            "title",
            "description",
            "documents_count",
        )


class CollaborationSerializer(serializers.ModelSerializer):
    identifiers = IdentifierSerializer(many=True, read_only=True)
    documents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AuthorityOrganization
        fields = ("id", "name", "type", "identifiers", "documents_count")


class StructureResearcherSerializer(serializers.ModelSerializer):
    """researcher of a structure, with its position (annotated in structure modules)"""

    user = ProjectUserMinimalSerializer(read_only=True)
    position_code = serializers.CharField(read_only=True, allow_null=True)
    position = serializers.SerializerMethodField()

    class Meta:
        model = Researcher
        fields = ("id", "display_name", "user", "position_code", "position")

    def get_position(self, instance: Researcher) -> str | None:
        code = getattr(instance, "position_code", None)
        if not code:
            return None
        if code in ResearcherStructure.PositionCode:
            return str(ResearcherStructure.PositionCode(code).label)
        # unknown code from crisalid
        return code
