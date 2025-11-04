from django.db.models import Count, Q, QuerySet


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
