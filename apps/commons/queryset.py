from collections import defaultdict
from typing import Self

from django.db import models


class MultipleIdQuerySet(models.QuerySet):
    """queryset/manager to filter queryset by id or slug"""

    def _build_identifiers_query(self, identifiers: tuple[str | int]):
        query = defaultdict(list)
        for iden in identifiers:
            field = self.model.get_id_field_name(iden)
            query[field].append(iden)

        return {f"{field}__in": ids for field, ids in query.items()}

    def slug_or_id(self, identifier: str | int) -> Self:
        return self.filter(**self._build_identifiers_query((identifier,)))

    def slug_or_ids(self, identifiers: tuple[str | int]) -> Self:
        return self.filter(**self._build_identifiers_query(identifiers))
