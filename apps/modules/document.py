from django.db.models import (
    QuerySet,
)
from django.db.models.manager import BaseManager

from apps.modules.base import AbstractModules, register_module
from services.crisalid.models import Document
from services.crisalid.models.document import DocumentJournal


@register_module(Document)
class DocumentModules(AbstractModules):
    instance: Document

    def similars(self) -> QuerySet[Document]:
        return self.instance.similars()

    def citations(self) -> BaseManager[DocumentJournal]:
        return self.instance.document_journals.all()
