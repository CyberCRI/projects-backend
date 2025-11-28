from django.db.models import Case, Count, Q, QuerySet, Value, When


class CrisalidQuerySet(QuerySet):
    def from_identifiers(self, identifiers: list):
        """filter by identifiers"""
        from services.crisalid.models import Identifier

        pks = set()
        filters = Q()
        for identifier in identifiers:
            if isinstance(identifier, int):
                pks.add(identifier)
            elif isinstance(identifier, Identifier):
                pks.add(identifier.pk)
            elif isinstance(identifier, dict):
                filters |= Q(
                    identifiers__value=identifier["value"],
                    identifiers__harvester=identifier["harvester"],
                )

        return (
            self.filter(Q(identifiers__pk__in=pks) | filters)
            .order_by("pk")
            .distinct("pk")
        )


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
