from typing import Self

from django.db import models
from django.db.models import OuterRef, Subquery
from pgvector.django import CosineDistance


class EmbdeddingQuerySet(models.QuerySet):

    def vector_search(
        self, item: models.Model | int | OuterRef, thresold: float | None = None
    ) -> Self:

        qs_embedding_instance = self.filter(item=item, is_visible=True)
        qs_embedding = qs_embedding_instance.values("embedding")[:1]

        qs_similar = (
            self.annotate(
                cosine=CosineDistance(
                    "embedding",
                    Subquery(qs_embedding),
                )
            )
            .exclude(pk__in=qs_embedding_instance)
            .order_by("cosine")
        )

        if thresold is not None:
            qs_similar = qs_similar.filter(cosine__lte=thresold)

        return qs_similar
