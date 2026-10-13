from django.db.models import BaseManager, Count, Q

from apps.modules.base import AbstractModules, ignore_method, register_module
from services.crisalid.models import (
    Document,
    DocumentTypeCentralized,
    Researcher,
)


@register_module(Researcher)
class ResearcherModules(AbstractModules):
    instance: Researcher

    def identifiers(self):
        return self.instance.identifiers.all()

    @ignore_method
    def documents(self) -> BaseManager[Document]:
        return self.instance.documents.all()

    # create dynamicly all research plucations types to modules
    for name, document_types in DocumentTypeCentralized.items():

        def _name(self, document_types=document_types):
            return self.documents().filter(document_type__in=document_types)

        _name.__name__ = name
        locals()[name] = _name

    def similars(self) -> BaseManager[Researcher]:
        return self.instance.similars()

    def affiliated(self) -> BaseManager[Researcher]:
        # TODO: filter documents by only where researcher is Authors/Co-Authors ...ect
        #       not only reviewer/cited ...ect
        researchers = Researcher.objects.filter(user__in=self.user.get_user_queryset())
        documents_qs = self.documents()
        return (
            researchers.filter(documents__in=documents_qs)
            .annotate(
                contributions_count=Count(
                    "documents", filter=Q(documents__in=documents_qs), distinct=True
                )
            )
            .order_by("-contributions_count")
        )
