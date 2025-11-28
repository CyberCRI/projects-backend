import datetime

from django import test

from apps.accounts.models import ProjectUser
from services.crisalid.factories import CrisalidConfigFactory
from services.crisalid.models import Document, Identifier, Researcher
from services.crisalid.populates import PopulateDocument, PopulateResearcher


class TestPopulateResearcher(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()

    def test_create_researcher(self):
        popu = PopulateResearcher(self.config)
        data = {
            "uid": "05-11-1995-uuid",
            "names": [
                {
                    "first_names": [{"value": "marty", "language": "fr"}],
                    "last_names": [{"value": "mcfly", "language": "fr"}],
                }
            ],
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value}
            ],
        }

        new_obj = popu.single(data)

        # check obj from db
        obj = Researcher.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.given_name, "marty")
        self.assertEqual(obj.family_name, "mcfly")
        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    def test_no_change_researcher(self):
        data = {
            "uid": "05-11-1995-uuid",
            "names": [
                {
                    "first_names": [{"value": "marty", "language": "fr"}],
                    "last_names": [{"value": "mcfly", "language": "fr"}],
                }
            ],
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value}
            ],
        }
        # create same object in db
        researcher = Researcher.objects.create(given_name="marty", family_name="mcfly")
        iden = Identifier.objects.create(
            value="hals-truc", harvester=Identifier.Harvester.HAL.value
        )
        researcher.identifiers.add(iden)
        popu = PopulateResearcher(self.config)

        new_obj = popu.single(data)

        # check no new object are created
        self.assertEqual(Researcher.objects.count(), 1)
        self.assertEqual(Identifier.objects.count(), 1)

        # check obj from db
        obj = Researcher.objects.first()
        self.assertEqual(new_obj, obj)

        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    def test_update_identifiers(self):
        data = {
            "names": [
                {
                    "first_names": [{"value": "marty", "language": "fr"}],
                    "last_names": [{"value": "mcfly", "language": "fr"}],
                }
            ],
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value}
            ],
        }
        # create same object in db
        researcher = Researcher.objects.create(given_name="marty", family_name="mcfly")
        iden = Identifier.objects.create(
            value="hals-truc", harvester=Identifier.Harvester.HAL.value
        )
        researcher.identifiers.add(iden)

        data["identifiers"].append(
            {"value": "000-666-999", "type": Identifier.Harvester.ORCID.value}
        )
        popu = PopulateResearcher(self.config)
        popu.single(data)

        # check no new object are created
        self.assertEqual(Researcher.objects.count(), 1)
        self.assertEqual(Identifier.objects.count(), 2)

        # check obj from db
        obj = Researcher.objects.first()
        iden = obj.identifiers.last()
        self.assertEqual(iden.value, "000-666-999")
        self.assertEqual(iden.harvester, Identifier.Harvester.ORCID.value)

    def test_create_user_researcher(self):
        data = {
            "uid": "05-11-1995-uuid",
            "first_names": "marty",
            "last_names": "mcfly",
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value},
                {"value": "eppn@lpi.com", "type": Identifier.Harvester.EPPN.value},
            ],
        }
        popu = PopulateResearcher(self.config)
        popu.single(data)

        user = ProjectUser.objects.first()
        # check no new object are created
        self.assertEqual(user.given_name, data["first_names"])
        self.assertEqual(user.family_name, data["last_names"])
        self.assertEqual(user.email, "eppn@lpi.com")

    def test_match_user_researcher(self):
        data = {
            "uid": "05-11-1995-uuid",
            "first_names": "marty",
            "last_names": "mcfly",
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value},
                {"value": "eppn@lpi.com", "type": Identifier.Harvester.EPPN.value},
            ],
        }
        # a project user already exists with same eepn
        user = ProjectUser.objects.create(email="eppn@lpi.com")

        popu = PopulateResearcher(self.config)
        popu.single(data)

        researcher = Researcher.objects.first()
        # given_name and family_name is not set in projects user
        # we don't change user value (only matching)
        self.assertEqual(user.given_name, "")
        self.assertEqual(user.family_name, "")

        self.assertEqual(researcher.user, user)


class TestPopulateDocument(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()

    def test_create_publication(self):
        popu = PopulateDocument(self.config)
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
                                {"type": "eppn", "value": "marty.mcfly@non-de-zeus.fr"},
                                {"type": "idref", "value": "4545454545454"},
                                {"type": "local", "value": "v55555"},
                            ],
                        }
                    ],
                }
            ],
            "recorded_by": [
                {
                    "uid": "hals-truc",
                    "harvester": Identifier.Harvester.HAL.value,
                    "value": "",
                }
            ],
        }

        new_obj = popu.single(data)

        # check obj from db
        obj = Document.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.title, "fiction")
        self.assertEqual(obj.identifiers.count(), 1)
        self.assertEqual(obj.document_type, Document.DocumentType.UNKNOWN.value)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    def test_sanitize_date(self):
        popu = PopulateDocument(self.config)

        self.assertEqual(
            popu.sanitize_date("1999"), datetime.datetime(1999, 1, 1).date()
        )
        self.assertEqual(
            popu.sanitize_date("1999-05"), datetime.datetime(1999, 5, 1).date()
        )
        self.assertEqual(
            popu.sanitize_date("1999-05-11"), datetime.datetime(1999, 5, 11).date()
        )
        self.assertEqual(popu.sanitize_date(""), None)
        self.assertEqual(popu.sanitize_date(None), None)
        self.assertEqual(popu.sanitize_date("invalidDate"), None)

    def test_sanitize_titles(self):
        popu = PopulateDocument(self.config)

        self.assertEqual(popu.sanitize_languages([]), "")
        self.assertEqual(
            popu.sanitize_languages([{"language": "en", "value": "en-title"}]),
            "en-title",
        )
        self.assertEqual(
            popu.sanitize_languages(
                [
                    {"language": "en", "value": "en-title"},
                    {"language": "fr", "value": "fr-title"},
                ]
            ),
            "en-title",
        )
        self.assertEqual(
            popu.sanitize_languages(
                [
                    {"language": "es", "value": "es-title"},
                    {"language": "fr", "value": "fr-title"},
                ]
            ),
            "fr-title",
        )
        self.assertEqual(
            popu.sanitize_languages([{"language": "es", "value": "es-title"}]),
            "es-title",
        )

    def test_sanitize_document_type(self):
        popu = PopulateDocument(self.config)

        self.assertEqual(
            popu.sanitize_document_type(None),
            Document.DocumentType.UNKNOWN.value,
        )
        self.assertEqual(
            popu.sanitize_document_type("invalid-Document-type"),
            Document.DocumentType.UNKNOWN.value,
        )
        self.assertEqual(
            popu.sanitize_document_type(
                Document.DocumentType.AUDIOVISUAL_DOCUMENT.value
            ),
            Document.DocumentType.AUDIOVISUAL_DOCUMENT.value,
        )
