from functools import cached_property

from django.db.models import (
    Case,
    CharField,
    Count,
    IntegerField,
    OuterRef,
    Subquery,
    Value,
    When,
)
from django.db.models.manager import BaseManager

from apps.modules.base import AbstractModules, ignore_method, register_module
from apps.skills.models import Tag
from services.crisalid.models import (
    AuthorityOrganization,
    Document,
    DocumentJournal,
    DocumentTypeCentralized,
    Researcher,
    ResearcherStructure,
    Structure,
    StructureRelation,
)


@register_module(Structure)
class StructureModules(AbstractModules):
    instance: Structure

    @cached_property
    def _structures_pks(self) -> list[int]:
        """the structure and its sub-structures"""
        return [self.instance.pk, *(s.pk for s in self.instance.descendants())]

    def _position_code(self, **relation) -> Subquery:
        """crisalid position (HCERES code) of the researcher in the structure"""
        return Subquery(
            ResearcherStructure.objects.filter(
                ResearcherStructure.active_query(),
                researcher=OuterRef("pk"),
                structure__in=self._structures_pks,
                **relation,
            )
            .exclude(position_code="")
            # position in the structure first, then in sub-structures
            .annotate(
                own_structure=Case(
                    When(structure=self.instance, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("own_structure", "position_code")
            .values("position_code")[:1],
            output_field=CharField(),
        )

    def researchers(self, relation_type: str | None = None) -> BaseManager[Researcher]:
        """researchers with an active relation to the structure or its sub-structures

        :param relation_type: only researchers with this relation (membership/employment)
        """
        relation = {"relation_type": relation_type} if relation_type else {}
        # same filter() call, so all conditions apply to the same relation
        researchers = Researcher.objects.filter(
            ResearcherStructure.active_query("researcherstructure__"),
            researcherstructure__structure__in=self._structures_pks,
            **{f"researcherstructure__{key}": value for key, value in relation.items()},
        )
        return (
            self.user.get_user_related_queryset(researchers)
            .distinct()
            .select_related("user")
            .annotate(position_code=self._position_code(**relation))
        )

    @ignore_method
    def documents(self) -> BaseManager[Document]:
        return Document.objects.filter(contributors__in=self.researchers()).distinct()

    # create dynamicly all research plucations types to modules
    for name, document_types in DocumentTypeCentralized.items():

        def _name(self, document_types=document_types):
            return self.documents().filter(document_type__in=document_types)

        _name.__name__ = name
        locals()[name] = _name

    def sub_structures(self) -> BaseManager[Structure]:
        return self.user.get_people_group_related_queryset(
            self.instance.children().select_related("people_group")
        )

    def parent_structures(self) -> BaseManager[Structure]:
        return self.user.get_people_group_related_queryset(
            self.instance.parents().select_related("people_group")
        )

    def _supervision_position(self, **relation) -> Subquery:
        """position of the supervision (crisalid "member_of") between two structures"""
        return Subquery(
            StructureRelation.objects.filter(
                StructureRelation.active_query(),
                relation_type=StructureRelation.RelationType.MEMBER_OF,
                **relation,
            )
            .order_by("position")
            .values("position")[:1],
            output_field=CharField(),
        )

    def supervising_structures(self) -> BaseManager[Structure]:
        """structures supervising the structure, with the supervision position"""
        # same filter() call, so all conditions apply to the same relation
        structures = Structure.objects.filter(
            StructureRelation.active_query("reverse_relations__"),
            reverse_relations__structure=self.instance,
            reverse_relations__relation_type=StructureRelation.RelationType.MEMBER_OF,
        )
        return (
            self.user.get_people_group_related_queryset(structures)
            .distinct()
            .select_related("people_group")
            .annotate(
                position=self._supervision_position(
                    structure=self.instance, related_structure=OuterRef("pk")
                )
            )
        )

    def supervised_structures(self) -> BaseManager[Structure]:
        """structures supervised by the structure, with the supervision position"""
        # same filter() call, so all conditions apply to the same relation
        structures = Structure.objects.filter(
            StructureRelation.active_query("relations__"),
            relations__related_structure=self.instance,
            relations__relation_type=StructureRelation.RelationType.MEMBER_OF,
        )
        return (
            self.user.get_people_group_related_queryset(structures)
            .distinct()
            .select_related("people_group")
            .annotate(
                position=self._supervision_position(
                    structure=OuterRef("pk"), related_structure=self.instance
                )
            )
        )

    def research_domains(self) -> BaseManager[Tag]:
        # filter before annotate: only structure documents are counted
        return (
            Tag.objects.filter(documents__in=self.documents())
            .annotate(documents_count=Count("documents", distinct=True))
            .order_by("-documents_count", "title")
        )

    def collaborations(self) -> BaseManager[AuthorityOrganization]:
        # filter before annotate: only structure documents are counted
        return (
            AuthorityOrganization.objects.filter(documents__in=self.documents())
            .annotate(documents_count=Count("documents", distinct=True))
            .order_by("-documents_count", "name")
        )

    def citations(self) -> BaseManager[DocumentJournal]:
        return DocumentJournal.objects.filter(document__in=self.documents())
