from django.db.models import (
    QuerySet,
)

from apps.modules.base import AbstractModules, register_module
from services.crisalid.models import Document


@register_module(Document)
class DocumentModules(AbstractModules):
    instance: Document

    def similars(self) -> QuerySet[Document]:
        return self.instance.similars()
