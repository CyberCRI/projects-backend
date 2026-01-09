import datetime

from django import test

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings, ProjectUser
from services.crisalid.factories import CrisalidConfigFactory
from services.crisalid.models import Document, Identifier, Researcher, Structure
from services.crisalid.populates import PopulateDocument, PopulateResearcher
from services.crisalid.populates.structure import PopulateStructure


class TestPopulateResearcher(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()
        cls.popu = PopulateResearcher(cls.config)

    def test_create_researcher(self):
        data = {
            "uid": "05-11-1995-uuid",
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

        new_obj = self.popu.single(data)

        # check obj from db
        obj = Researcher.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.given_name, "marty")
        self.assertEqual(obj.family_name, "mcfly")
        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    def test_create_researcher_whithout_identifiers(self):
        data = {
            "uid": "05-11-1995-uuid",
            "names": [
                {
                    "first_names": [{"value": "marty", "language": "fr"}],
                    "last_names": [{"value": "mcfly", "language": "fr"}],
                }
            ],
            "identifiers": [],
        }

        new_obj = self.popu.single(data)

        self.assertIsNone(new_obj)
        self.assertEqual(Researcher.objects.count(), 0)

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
                {"value": "hals-truc", "harvester": Identifier.Harvester.HAL.value}
            ],
        }
        # create same object in db
        researcher = Researcher.objects.create(given_name="marty", family_name="mcfly")
        iden = Identifier.objects.create(
            value="hals-truc", harvester=Identifier.Harvester.HAL.value
        )
        researcher.identifiers.add(iden)

        new_obj = self.popu.single(data)

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
                {"value": "hals-truc", "harvester": Identifier.Harvester.HAL.value}
            ],
        }
        # create same object in db
        researcher = Researcher.objects.create(given_name="marty", family_name="mcfly")
        iden = Identifier.objects.create(
            value="hals-truc", harvester=Identifier.Harvester.HAL.value
        )
        researcher.identifiers.add(iden)

        data["identifiers"].append(
            {"value": "000-666-999", "harvester": Identifier.Harvester.ORCID.value}
        )
        self.popu.single(data)

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
            "names": [
                {
                    "first_names": [{"value": "Marty", "language": "fr"}],
                    "last_names": [{"value": "Mcfly", "language": "fr"}],
                }
            ],
            "identifiers": [
                {"value": "hals-truc", "harvester": Identifier.Harvester.HAL.value},
                {"value": "eppn@lpi.com", "harvester": Identifier.Harvester.EPPN.value},
            ],
        }
        self.popu.single(data)

        user = ProjectUser.objects.first()
        # check no new object are created
        self.assertEqual(user.given_name, "Marty")
        self.assertEqual(user.family_name, "Mcfly")
        self.assertEqual(user.email, "eppn@lpi.com")
        self.assertEqual(
            user.privacy_settings.publication_status,
            PrivacySettings.PrivacyChoices.ORGANIZATION.value,
        )

    def test_match_user_researcher(self):
        data = {
            "uid": "05-11-1995-uuid",
            "names": [
                {
                    "first_names": [{"value": "Marty", "language": "fr"}],
                    "last_names": [{"value": "Mcfly", "language": "fr"}],
                }
            ],
            "identifiers": [
                {"value": "hals-truc", "harvester": Identifier.Harvester.HAL.value},
                {"value": "eppn@lpi.com", "harvester": Identifier.Harvester.EPPN.value},
            ],
        }
        # a project user already exists with same eepn
        user = UserFactory(email="eppn@lpi.com")
        self.assertEqual(
            user.privacy_settings.publication_status,
            PrivacySettings.PrivacyChoices.PUBLIC.value,
        )

        self.popu.single(data)

        researcher = Researcher.objects.select_related("user").first()
        self.assertEqual(researcher.user, user)
        # user already created, so given_name and family_name is not changed from crislaid event
        self.assertNotEqual(user.given_name, "Marty")
        self.assertNotEqual(user.family_name, "Mcfly")

        # privacy settings are not changed
        self.assertEqual(
            researcher.user.privacy_settings.publication_status,
            PrivacySettings.PrivacyChoices.PUBLIC.value,
        )


class TestPopulateDocument(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()
        cls.popu = PopulateDocument(cls.config)

    def test_create_publication(self):
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

        new_obj = self.popu.single(data)

        # check obj from db
        obj = Document.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.title, "fiction")
        self.assertEqual(obj.identifiers.count(), 1)
        self.assertEqual(obj.document_type, Document.DocumentType.UNKNOWN.value)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    def test_create_document_whitout_identifiers(self):
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
            "recorded_by": [],
        }

        new_obj = self.popu.single(data)

        # check obj from db
        self.assertIsNone(new_obj)
        self.assertEqual(Document.objects.count(), 0)

    def test_sanitize_date(self):
        self.assertEqual(
            self.popu.sanitize_date("1999"), datetime.datetime(1999, 1, 1).date()
        )
        self.assertEqual(
            self.popu.sanitize_date("1999-05"), datetime.datetime(1999, 5, 1).date()
        )
        self.assertEqual(
            self.popu.sanitize_date("1999-05-11"), datetime.datetime(1999, 5, 11).date()
        )
        self.assertEqual(self.popu.sanitize_date(""), None)
        self.assertEqual(self.popu.sanitize_date(None), None)
        self.assertEqual(self.popu.sanitize_date("invalidDate"), None)

    def test_sanitize_titles(self):
        self.assertEqual(self.popu.sanitize_languages([]), "")
        self.assertEqual(
            self.popu.sanitize_languages([{"language": "en", "value": "en-title"}]),
            "en-title",
        )
        self.assertEqual(
            self.popu.sanitize_languages(
                [
                    {"language": "en", "value": "en-title"},
                    {"language": "fr", "value": "fr-title"},
                ]
            ),
            "en-title",
        )
        self.assertEqual(
            self.popu.sanitize_languages(
                [
                    {"language": "es", "value": "es-title"},
                    {"language": "fr", "value": "fr-title"},
                ]
            ),
            "fr-title",
        )
        self.assertEqual(
            self.popu.sanitize_languages([{"language": "es", "value": "es-title"}]),
            "es-title",
        )

    def test_sanitize_document_type(self):
        self.assertEqual(
            self.popu.sanitize_document_type(None),
            Document.DocumentType.UNKNOWN.value,
        )
        self.assertEqual(
            self.popu.sanitize_document_type("invalid-Document-type"),
            Document.DocumentType.UNKNOWN.value,
        )
        self.assertEqual(
            self.popu.sanitize_document_type(
                Document.DocumentType.AUDIOVISUAL_DOCUMENT.value
            ),
            Document.DocumentType.AUDIOVISUAL_DOCUMENT.value,
        )


class TestPopulateStructure(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()
        cls.popu = PopulateStructure(cls.config)

    def test_create_structure(self):
        data = {
            "acronym": "LabEx CAP",
            "names": [{"language": "fr", "value": "CAP"}],
            "identifiers": [{"harvester": "local", "value": "DGI01"}],
        }

        new_obj = self.popu.single(data)

        # check obj from db
        obj = Structure.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.acronym, "LabEx CAP")
        self.assertEqual(obj.name, "CAP")
        self.assertEqual(obj.organization, self.config.organization)
        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "DGI01")
        self.assertEqual(iden.harvester, "local")

    def test_create_structure_whitout_identifiers(self):
        data = {
            "acronym": "LabEx CAP",
            "names": [{"language": "fr", "value": "CAP"}],
            "identifiers": [],
        }

        new_obj = self.popu.single(data)

        # check obj from db
        obj = Structure.objects.first()
        self.assertIsNone(obj)
        self.assertIsNone(new_obj)
