from rest_framework import serializers

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.fields import PrivacySettingProtectedMethodField
from apps.commons.serializers import PrivacySerializer
from apps.files.serializers import ImageSerializer
from apps.modules.serializers import ModulesSerializers
from apps.skills.models import Tag
from apps.skills.serializers import TagSerializer
from services.crisalid.models import (
    AuthorityOrganization,
    Award,
    Document,
    DocumentDomains,
    DocumentJournal,
    Journal,
    Patent,
    Researcher,
    ResearcherDomains,
    ResearcherStructure,
    Structure,
)
from services.crisalid.models.award import AwardContributor
from services.crisalid.models.funding import Funding
from services.crisalid.models.teaching import Teaching, TeachingDomain
from services.translator.serializers import auto_translated


class ProjectUserMinimalSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    profile_picture = ImageSerializer()

    class Meta:
        model = ProjectUser
        fields = ("id", "display_name", "slug", "profile_picture")

    def get_display_name(self, instance: ProjectUser) -> str:
        return str(instance)


class IdentifierSerializer(serializers.Serializer):
    """identifiers of any crisalid model (ResearcherIdentifier, DocumentIdentifier ...)"""

    harvester = serializers.CharField(read_only=True)
    value = serializers.CharField(read_only=True)


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


class ResearcherSerializerSuperLight(ResearcherSerializerLight):
    class Meta(ResearcherSerializerLight.Meta):
        fields = (
            "id",
            "display_name",
            "short_bio",
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
    researchers = ResearcherSerializerSuperLight(many=True)

    class Meta:
        model = Patent
        fields = ("id", "name", "description", "date", "link", "researchers")


@auto_translated
class PatentSerializerLight(PatentSerializer):
    class Meta(PatentSerializer.Meta):
        fields = ("id", "name", "description", "date", "link")


@auto_translated
class AwardSerializer(serializers.ModelSerializer):
    researchers = ResearcherSerializerSuperLight(many=True)

    class Meta:
        model = Award
        fields = ("id", "name", "description", "researchers")


@auto_translated
class AwardSerializerLight(AwardSerializer):
    class Meta(AwardSerializer.Meta):
        fields = ("id", "name", "description")


class AwardContributorSerializer(serializers.ModelSerializer):
    award = AwardSerializerLight()

    class Meta:
        model = AwardContributor
        fields = ("id", "award", "date", "link")


@auto_translated
class FundingSerializer(serializers.ModelSerializer):
    researchers = ResearcherSerializerSuperLight(many=True)

    class Meta:
        model = Funding
        fields = (
            "id",
            "name",
            "description",
            "prices",
            "currency",
            "start_date",
            "end_date",
            "project_id",
            "researchers",
        )


@auto_translated
class FundingLightSerializer(FundingSerializer):
    class Meta(FundingSerializer.Meta):
        model = Funding
        fields = (
            "id",
            "name",
            "description",
            "prices",
            "currency",
            "start_date",
            "end_date",
            "project_id",
        )


class TeachingDomainSerializer(serializers.ModelSerializer):
    domain = TagSerializer()

    class Meta:
        model = TeachingDomain
        fields = (
            "domain",
            "level",
        )


@auto_translated
class TeachingSerializer(serializers.ModelSerializer):
    researcher = ResearcherSerializerSuperLight()
    domains = TeachingDomainSerializer(many=True)

    class Meta:
        model = Teaching
        fields = (
            "id",
            "name",
            "description",
            "name",
            "description",
            "spec",
            "level",
            "link",
            "researcher",
            "domains",
        )


@auto_translated
class TeachingLightSerializer(TeachingSerializer):
    class Meta(TeachingSerializer.Meta):
        model = Teaching
        fields = (
            "id",
            "name",
            "description",
            "name",
            "description",
            "spec",
            "level",
            "link",
            "researcher",
            "domains",
        )


class StructurePeopleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeopleGroup
        fields = ("id", "slug", "name")


@auto_translated
class StructureSerializer(ModulesSerializers, serializers.ModelSerializer):
    people_group = StructurePeopleGroupSerializer(read_only=True)

    class Meta:
        model = Structure
        fields = (
            "id",
            "name",
            "acronym",
            "description",
            "generic_type",
            "national_type",
            "main_mission",
            "external",
            "people_group",
            "modules",
        )


@auto_translated
class StructureLightSerializer(StructureSerializer):
    class Meta(StructureSerializer.Meta):
        fields = (
            "id",
            "name",
            "acronym",
            "generic_type",
            "national_type",
            "main_mission",
            "external",
            "people_group",
            "modules",
        )
        modules_keys = ()


@auto_translated
class StructureSupervisionSerializer(StructureSerializer):
    """supervising/supervised structure, with the supervision position (annotated in structure modules)"""

    position = serializers.CharField(read_only=True, allow_null=True)

    class Meta(StructureSerializer.Meta):
        fields = (
            "id",
            "name",
            "acronym",
            "generic_type",
            "national_type",
            "main_mission",
            "external",
            "people_group",
            "position",
        )


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


class ResearcherStructureSerializer(serializers.ModelSerializer):
    """researcher of a structure, with its position (annotated in structure modules)"""

    position_code = serializers.CharField(read_only=True, allow_null=True)
    position = serializers.SerializerMethodField()

    structure = StructureLightSerializer()

    class Meta:
        model = ResearcherStructure
        fields = (
            "id",
            "structure",
            "relation_type",
            "position",
            "position_code",
        )

    def get_position(self, instance: Researcher) -> str | None:
        code = getattr(instance, "position_code", None)
        if not code:
            return None
        if code in ResearcherStructure.PositionCode:
            return str(ResearcherStructure.PositionCode(code).label)
        # unknown code from crisalid
        return code
