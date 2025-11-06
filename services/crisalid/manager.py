from django.db.models import Case, Count, Q, QuerySet, Value, When


class DocumentQuerySet(QuerySet):
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
