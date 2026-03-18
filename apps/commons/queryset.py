from collections import defaultdict
from typing import Self

from django.contrib.postgres.fields import ArrayField
from django.db import models


class MultipleIdsQuerySet(models.QuerySet):
    """queryset/manager to filter queryset by id or slug"""

    def _get_related_field(self, model: models.Model, field: str) -> models.Field:
        """traverse fields query to get real field model"""

        acutal_model = model
        *traverse, last = field.split("__")
        for sub in traverse:
            acutal_model = acutal_model._meta.get_field(sub).related_model
        return acutal_model._meta.get_field(last)

    def build_identifiers_query(self, identifiers: tuple[str | int]) -> models.Q:
        query = defaultdict(set)

        for identifier in identifiers:
            field = self.model.get_id_field_name(identifier)
            if field == "slug" and hasattr(self.model, "outdated_slugs"):
                fields = (field, "outdated_slugs")
            else:
                fields = (field,)

            for field in fields:
                query[field].add(str(identifier))

        final_query = models.Q()
        for field, values in query.items():
            field_cls = self._get_related_field(self.model, field)
            if isinstance(field_cls, ArrayField):
                lookup = "__contains"
            else:
                lookup = "__in"

            final_query |= models.Q(**{f"{field}{lookup}": list(values)})

        return final_query

    def slug_or_id(self, identifier: str | int) -> Self:
        return self.filter(self.build_identifiers_query((identifier,)))

    def slug_or_ids(self, identifiers: tuple[str | int]) -> Self:
        return self.filter(self.build_identifiers_query(identifiers))
