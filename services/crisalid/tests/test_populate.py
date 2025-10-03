from django import test

from services.crisalid.models import Document, Identifier, Researcher
from services.crisalid.populate import PopulateDocumentCrisalid, PopulateResearcher


class TestPopulateResearcher(test.TestCase):
    def test_create_researcher(self):
        popu = PopulateResearcher()
        data = {
            "uid": "05-11-1995-uuid",
            "display_name": "marty mcfly",
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value}
            ],
        }

        new_obj = popu.single(data)

        # check obj from db
        obj = Researcher.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.display_name, "marty mcfly")
        self.assertEqual(obj.crisalid_uid, "05-11-1995-uuid")
        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    def test_no_change_researcher(self):
        data = {
            "uid": "05-11-1995-uuid",
            "display_name": "marty mcfly",
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value}
            ],
        }
        # create same object in db
        researcher = Researcher.objects.create(
            crisalid_uid=data["uid"], display_name=data["display_name"]
        )
        iden = Identifier.objects.create(
            value="hals-truc", harvester=Identifier.Harvester.HAL.value
        )
        researcher.identifiers.add(iden)
        popu = PopulateResearcher()

        new_obj = popu.single(data)

        # check no new object are created
        self.assertEqual(Researcher.objects.count(), 1)
        self.assertEqual(Identifier.objects.count(), 1)

        # check obj from db
        obj = Researcher.objects.first()
        self.assertEqual(new_obj, obj)

        self.assertEqual(obj.display_name, "marty mcfly")
        self.assertEqual(obj.crisalid_uid, "05-11-1995-uuid")
        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)


class TestPopulateDocument(test.TestCase):
    def test_create_document(self):
        popu = PopulateDocumentCrisalid()
        data = {
            "uid": "05-11-1995-uuid",
            "document_type": None,
            "titles": [
                {"language": "en", "value": "fiction"},
            ],
            "publication_date": "1999",
            "recorded_by": [
                {
                    "uid": "hals-truc",
                    "harvester": Identifier.Harvester.HAL.value,
                    "value": "",
                    "harvested_for": [],
                }
            ],
        }

        new_obj = popu.single(data)

        # check obj from db
        obj = Document.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.title, "fiction")
        self.assertEqual(obj.crisalid_uid, "05-11-1995-uuid")
        self.assertEqual(obj.identifiers.count(), 1)
        self.assertEqual(obj.document_type, None)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)
