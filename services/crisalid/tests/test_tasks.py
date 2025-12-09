from unittest.mock import patch

from django import test

from services.crisalid.factories import (
    CrisalidConfigFactory,
    DocumentFactory,
    ResearcherFactory,
    faker,
)
from services.crisalid.models import Document, Identifier, Researcher
from services.crisalid.tasks import (
    create_document,
    create_researcher,
    delete_document,
    delete_researcher,
)


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

    @patch("services.crisalid.interface.Client")
    def test_create_researcher(self, client_gql):
        # other check/tests in test_views.py
        fields = {"uid": "05-11-1995-uuid"}
        data = {
            "names": [
                {
                    "first_names": [{"value": "marty", "language": "fr"}],
                    "last_names": [{"value": "mcfly", "language": "fr"}],
                }
            ],
            "identifiers": [
                {"value": "hals-truc", "harvester": Identifier.Harvester.HAL.value}
            ],
        }

        client_gql().execute.return_value = {"people": [data]}

        create_researcher(self.config.pk, fields)

        # check obj from db
        obj = Researcher.objects.first()

        self.assertEqual(obj.given_name, "marty")
        self.assertEqual(obj.family_name, "mcfly")
        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    @patch("services.crisalid.interface.Client")
    def test_create_document_empty(self, client_gql):
        fields = {"uid": faker.uuid4()}
        client_gql().execute.return_value = {"documents": []}

        self.assertEqual(Document.objects.count(), 0)
        create_document(self.config.pk, fields)
        self.assertEqual(Document.objects.count(), 0)

    @patch("services.crisalid.interface.Client")
    def test_create_document(self, client_gql):
        fields = {"uid": faker.uuid4()}
        data = {
            "uid": "05-11-1995-uuid",
            "document_type": None,
            "titles": [
                {"language": "en", "value": "fiction"},
            ],
            "abstracts": [
                {"language": "en", "value": "description"},
            ],
            "publication_date": "1999",
            "has_contributions": [
                {
                    "roles": ["http://id.loc.gov/vocabulary/relators/aut"],
                    "contributor": [
                        {
                            "uid": "local-v9034",
                            "names": [
                                {
                                    "first_names": [
                                        {"value": "Marty", "language": "fr"}
                                    ],
                                    "last_names": [
                                        {"value": "Mcfly", "language": "fr"}
                                    ],
                                }
                            ],
                            "identifiers": [
                                {
                                    "harvester": "eppn",
                                    "value": "marty.mcfly@non-de-zeus.fr",
                                },
                                {"harvester": "idref", "value": "4545454545454"},
                                {"harvester": "local", "value": "v55555"},
                            ],
                        }
                    ],
                }
            ],
            "recorded_by": [
                {
                    "harvester": Identifier.Harvester.HAL.value,
                    "value": "hals-truc",
                }
            ],
        }

        client_gql().execute.return_value = {"documents": [data]}

        create_document(self.config.pk, fields)
        # check obj from db
        obj = Document.objects.first()

        self.assertEqual(obj.title, "fiction")
        self.assertEqual(obj.identifiers.count(), 1)
        self.assertEqual(obj.document_type, Document.DocumentType.UNKNOWN.value)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)
