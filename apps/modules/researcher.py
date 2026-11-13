from django.db.models import Case, Count, Q, When
from django.db.models.manager import BaseManager

from apps.modules.base import (
    AbstractModules,
    ignore_method,
    organization_related,
    register_module,
)
from services.crisalid.constants import RolesCentralized
from services.crisalid.models import (
    Document,
    DocumentJournal,
    DocumentTypeCentralized,
    Researcher,
    ResearcherDomains,
)
from services.crisalid.models.award import AwardContributor
from services.crisalid.models.funding import Funding
from services.crisalid.models.patent import Patent
from services.crisalid.models.structure import ResearcherStructure
from services.crisalid.models.teaching import Teaching


@register_module(Researcher)
class ResearcherModules(AbstractModules):
    instance: Researcher

    @ignore_method
    def identifiers(self):
        return self.instance.identifiers.all()

    @ignore_method
    def public_identifiers(self):
        return self.identifiers().exclude(harvester__in=Researcher.PRIVACY_HARVESTER)

    @ignore_method
    def documents(self) -> BaseManager[Document]:
        return self.instance.documents.all()

    # create dynamicly all research plucations types to modules
    for name, document_types in DocumentTypeCentralized.items():

        def _name(self, document_types=document_types):
            return self.documents().filter(document_type__in=document_types)

        _name.__name__ = name
        locals()[name] = _name

    @organization_related
    def similars(self) -> BaseManager[Researcher]:
        return self.instance.similars()

    @organization_related
    def affiliated(self) -> BaseManager[Researcher]:
        # TODO: filter documents by only where researcher is Authors/Co-Authors ...ect
        #       not only reviewer/cited ...ect
        researchers = Researcher.objects.filter(user__in=self.user.get_user_queryset())
        documents_qs = self.documents()
        return (
            researchers.filter(documents__in=documents_qs)
            # exclude self
            .exclude(pk=self.instance.pk)
            .annotate(
                contributions_count=Count(
                    "documents", filter=Q(documents__in=documents_qs), distinct=True
                )
            )
            .order_by("-contributions_count")
        )

    def citations(self) -> BaseManager[DocumentJournal]:
        # calculate only citations in doucments where research is author/co-author ..ect
        documents = (
            self.documents()
            .filter(documentcontributor__roles__overlap=list(RolesCentralized.LEVEL_2))
            .distinct()
        )
        return DocumentJournal.objects.filter(document__in=documents)

    def domains(self) -> BaseManager[ResearcherDomains]:
        return self.instance.researcher_domains.all()

    def patents(self) -> BaseManager[Patent]:
        return self.instance.patents.all().prefetch_related("researchers")

    def awards(self) -> BaseManager[AwardContributor]:
        return self.instance.awards_conributor.all()

    def teachings(self) -> BaseManager[Teaching]:
        return self.instance.teachings.all()

    def fundings(self) -> BaseManager[Funding]:
        return self.instance.fundings.all()

    @organization_related
    def structures(self) -> BaseManager[ResearcherStructure]:
        priority_position_code = []
        for idx, (_, value) in enumerate(ResearcherStructure.PositionCode.choices):
            priority_position_code.append(When(position_code=value, then=idx))

        return (
            ResearcherStructure.objects.filter(researcher=self.instance)
            .filter(
                ResearcherStructure.active_query(),
            )
            .select_related("structure")
            .annotate(
                priority_position_code=Case(*priority_position_code, default=9999999)
            )
            .order_by("priority_position_code")
        )
