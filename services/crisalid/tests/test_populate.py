import datetime

from django import test

from apps.accounts.models import ProjectUser
from services.crisalid.models import Identifier, Publication, Researcher
from services.crisalid.populate import PopulatePublication, PopulateResearcher


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

    def test_update_identifiers(self):
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

        data["identifiers"].append(
            {"value": "000-666-999", "type": Identifier.Harvester.ORCID.value}
        )
        popu = PopulateResearcher()
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
            "display_name": "marty mcfly",
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value},
                {"value": "eppn@lpi.com", "type": Identifier.Harvester.EPPN.value},
            ],
        }
        popu = PopulateResearcher()
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
            "display_name": "marty mcfly",
            "identifiers": [
                {"value": "hals-truc", "type": Identifier.Harvester.HAL.value},
                {"value": "eppn@lpi.com", "type": Identifier.Harvester.EPPN.value},
            ],
        }
        # a project user already exists with same eepn
        user = ProjectUser.objects.create(email="eppn@lpi.com")

        popu = PopulateResearcher()
        popu.single(data)

        researcher = Researcher.objects.first()
        # given_name and family_name is not set in projects user
        # we don't change user value (only matching)
        self.assertEqual(user.given_name, "")
        self.assertEqual(user.family_name, "")

        self.assertEqual(researcher.user, user)


class TestPopulatePublication(test.TestCase):
    def test_create_publication(self):
        popu = PopulatePublication()
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
                            "display_name": "Marty Mcfly",
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
        obj = Publication.objects.first()
        self.assertEqual(obj, new_obj)

        self.assertEqual(obj.title, "fiction")
        self.assertEqual(obj.crisalid_uid, "05-11-1995-uuid")
        self.assertEqual(obj.identifiers.count(), 1)
        self.assertEqual(
            obj.publication_type, Publication.PublicationType.UNKNOWN.value
        )
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, Identifier.Harvester.HAL.value)

    def test_sanitize_date(self):
        popu = PopulatePublication()

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
        popu = PopulatePublication()

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

    def test_sanitize_publication_type(self):
        popu = PopulatePublication()

        self.assertEqual(
            popu.sanitize_publication_type(None),
            Publication.PublicationType.UNKNOWN.value,
        )
        self.assertEqual(
            popu.sanitize_publication_type("invalid-Publication-type"),
            Publication.PublicationType.UNKNOWN.value,
        )
        self.assertEqual(
            popu.sanitize_publication_type(
                Publication.PublicationType.AUDIOVISUAL_DOCUMENT.value
            ),
            Publication.PublicationType.AUDIOVISUAL_DOCUMENT.value,
        )
