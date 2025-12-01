from django import test

from services.crisalid.factories import (
    CrisalidConfigFactory,
    DocumentFactory,
    ResearcherFactory,
)
from services.crisalid.models import Document, Researcher
from services.crisalid.tasks import delete_document, delete_researcher


class TestCrisalidTasks(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()

    def test_delete_document(self):
        document = DocumentFactory()
        document_2 = DocumentFactory()

        fields = {
            "recorded_by": [
                {
                    "harvester": identifier.harvester,
                    "uid": identifier.value,
                }
                for identifier in document.identifiers.all()
            ]
        }

        delete_document(self.config.pk, fields)

        self.assertFalse(Document.objects.filter(pk=document.pk).exists())
        self.assertTrue(Document.objects.filter(pk=document_2.pk).exists())

    def test_delete_document_unknow(self):
        document = DocumentFactory()

        fields = {
            "recorded_by": [
                {
                    "harvester": identifier.harvester,
                    "uid": identifier.value + "rand",
                }
                for identifier in document.identifiers.all()
            ]
        }

        delete_document(self.config.pk, fields)

        self.assertTrue(Document.objects.filter(pk=document.pk).exists())

    def test_delete_researcher(self):
        researcher = ResearcherFactory()
        researcher_2 = ResearcherFactory()

        fields = {
            "identifiers": [
                {
                    "type": identifier.harvester,
                    "value": identifier.value,
                }
                for identifier in researcher.identifiers.all()
            ]
        }

        delete_researcher(self.config.pk, fields)

        self.assertFalse(Researcher.objects.filter(pk=researcher.pk).exists())
        self.assertTrue(Researcher.objects.filter(pk=researcher_2.pk).exists())

    def test_delete_research(self):
        researcher = ResearcherFactory()

        fields = {
            "identifiers": [
                {
                    "type": identifier.harvester,
                    "value": identifier.value + "rand",
                }
                for identifier in researcher.identifiers.all()
            ]
        }

        delete_researcher(self.config.pk, fields)

        self.assertTrue(Researcher.objects.filter(pk=researcher.pk).exists())

    def test_create_document(self):
        pass

    def test_create_researcher(self):
        pass
