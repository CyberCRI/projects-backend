from django.db.models import Q, QuerySet, Count

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
        for atter_name in dir(DocumentTypeCentralized):
            if atter_name.startswith("_"):
                continue

            document_types = getattr(DocumentTypeCentralized, atter_name)
            aggregate[atter_name] = Count("id", filter=Q(
                document_type__in=document_types
            ))
        
        return self.aggregate(**aggregate)
