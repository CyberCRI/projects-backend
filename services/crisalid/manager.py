from django.db import models
from django.db.models import Case, Count, Q, QuerySet, Value, When


class CrisalidQuerySet(QuerySet):
    def from_identifiers(self, identifiers: list, distinct=True):
        """filter by identifiers (owned by the model, related name "identifiers")
        identifiers is a list of:
            - identifier objects (ResearcherIdentifier, DocumentIdentifier ...)
            - dict: dict object with value/harvester key

            example:
             Researcher.objects.from_identifiers([
              ResearcherIdentifier(value="jhon.carter@mars.space", harvester="eppn"),
              {"harvester": "idref", "value": "4855993"}
             ])
        """
        filters = models.Q()
        for identifier in identifiers:
            if isinstance(identifier, dict):
                harvester, value = identifier["harvester"], identifier["value"]
            else:
                harvester, value = identifier.harvester, identifier.value
            filters |= models.Q(
                identifiers__harvester=harvester, identifiers__value=value
            )

        if not filters:
            return self.none()
        qs = self.filter(filters)
        if distinct:
            qs = qs.order_by("pk").distinct("pk")
        return qs


class DocumentQuerySet(CrisalidQuerySet):
    def group_count(self) -> dict[str, int]:
        """Calcultate all count by document centralized type
        return results like
        {
          "publication": 44,
          "conference": 32,
          ...
        }

        :return: analytics dict
        """
        from .models import DocumentTypeCentralized

        aggregate = {}
        for name, document_types in DocumentTypeCentralized.items():
            aggregate[name] = Count("id", filter=Q(document_type__in=document_types))

        return self.aggregate(**aggregate)

    def annotate_doctype_centralized(self) -> "DocumentQuerySet":
        from .models import Document, DocumentTypeCentralized

        cases = []
        for name, document_types in DocumentTypeCentralized.items():
            cases.append(When(document_type__in=document_types, then=Value(name)))

        return self.annotate(
            ann_document_type=Case(
                *cases, default=Value(Document.DocumentType.UNKNOWN.value)
            )
        )
