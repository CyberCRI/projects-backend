import datetime

from django import test
from django.core.exceptions import ValidationError

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, PrivacySettings, ProjectUser
from services.crisalid.factories import CrisalidConfigFactory
from services.crisalid.models import (
    AuthorityOrganization,
    Document,
    DocumentContributor,
    Identifier,
    Journal,
    Researcher,
    ResearcherStructure,
    Structure,
    StructureRelation,
)
from services.crisalid.populates import (
    PopulateDocument,
    PopulateResearcher,
    PopulateStructure,
)


def edges(*uids, **properties):
    return {
        "edges": [
            {
                "properties": {"start_date": None, "end_date": None, **properties},
                "node": {"uid": uid},
            }
            for uid in uids
        ]
    }


def structure_data(uid, part_of=None, member_of=None, **kwargs):
    return {
        "uid": uid,
        "external": False,
        "generic_type": "unit",
        "national_type": None,
        "types": ["OrganizationUnit"],
        "long_labels": [{"language": "fr", "value": f"long {uid}"}],
        "short_labels": [{"language": "fr", "value": uid}],
        "local_types": [],
        "descriptions": [],
        "identifiers": [{"harvester": "local", "value": uid}],
        "part_ofConnection": part_of or edges(),
        "member_ofConnection": member_of or edges(),
        **kwargs,
    }


def researcher_data(eppn, memberships=None, employments=None):
    return {
        "uid": eppn,
        "names": [
            {
                "first_names": [{"value": "marty", "language": "fr"}],
                "last_names": [{"value": "mcfly", "language": "fr"}],
            }
        ],
        "identifiers": [
            {"value": eppn, "harvester": Identifier.Harvester.EPPN.value},
            {"value": f"hal-{eppn}", "harvester": Identifier.Harvester.HAL.value},
        ],
        "membershipsConnection": memberships or edges(),
        "employmentsConnection": employments or edges(),
    }


def group_of(uid) -> PeopleGroup:
    return (
        Structure.objects.select_related("people_group__parent")
        .get(crisalid_uid=uid)
        .people_group
    )


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
                {
                    "value": "eppn@lpi.com",
                    "harvester": Identifier.Harvester.EPPN.value,
                },
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
                {
                    "value": "eppn@lpi.com",
                    "harvester": Identifier.Harvester.EPPN.value,
                },
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
            "titles": [{"language": "en", "value": "fiction"}],
            "abstracts": [{"language": "en", "value": "description"}],
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
                {"harvester": Identifier.Harvester.HAL.value, "value": "hals-truc"}
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
            "titles": [{"language": "en", "value": "fiction"}],
            "abstracts": [{"language": "en", "value": "description"}],
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
            "recorded_by": [],
        }

        new_obj = self.popu.single(data)

        # check obj from db
        self.assertIsNone(new_obj)
        self.assertEqual(Document.objects.count(), 0)

    def test_sanitize_date(self):
        self.assertEqual(
            self.popu.sanitize_date("1999"),
            datetime.datetime(1999, 1, 1).date(),
        )
        self.assertEqual(
            self.popu.sanitize_date("1999-05"),
            datetime.datetime(1999, 5, 1).date(),
        )
        self.assertEqual(
            self.popu.sanitize_date("1999-05-11"),
            datetime.datetime(1999, 5, 11).date(),
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
            self.popu.sanitize_document_type(Document.DocumentType.PRESENTATION.value),
            Document.DocumentType.PRESENTATION.value,
        )

    def test_sanitize_html_content(self):
        data = {
            "uid": "05-11-1995-uuid",
            "document_type": Document.DocumentType.ARTICLE.value,
            "titles": [{"language": "en", "value": "title <h1>with</h1> html"}],
            "abstracts": [
                {"language": "en", "value": "description <h1>with</h1> html"}
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
                                }
                            ],
                            "identifiers": [
                                {
                                    "harvester": "eppn",
                                    "value": "marty.mcfly@non-de-zeus.fr",
                                },
                            ],
                        }
                    ],
                }
            ],
            "recorded_by": [
                {"harvester": Identifier.Harvester.HAL.value, "value": "hals-truc"}
            ],
        }

        new_obj = self.popu.single(data)

        # html content are removed
        self.assertEqual(new_obj.description, "description with html")
        self.assertEqual(new_obj.title, "title with html")


class TestPopulateDocumentCrisalidData(test.TestCase):
    """journals, open access status and affiliations"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()
        cls.popu = PopulateDocument(cls.config)

    @staticmethod
    def contributor(eppn: str) -> dict:
        return {
            "names": [
                {
                    "first_names": [{"value": eppn, "language": "fr"}],
                    "last_names": [{"value": eppn, "language": "fr"}],
                }
            ],
            "identifiers": [
                {"harvester": "eppn", "value": eppn},
                {"harvester": "idref", "value": f"idref-{eppn}"},
            ],
        }

    def document_data(self, **kwargs) -> dict:
        return {
            "uid": "doc-uid",
            "document_type": "JournalArticle",
            "titles": [{"language": "en", "value": "fiction"}],
            "abstracts": [],
            "publication_date": "2020",
            "publishedInConnection": {
                "edges": [
                    {
                        "properties": {"volume": "270", "issue": "3", "pages": "1-9"},
                        "node": {
                            "uid": "journal-uid",
                            "titles": ["Journal of Biological Chemistry"],
                        },
                    }
                ]
            },
            "has_contributions": [
                {
                    "roles": ["http://id.loc.gov/vocabulary/relators/aut"],
                    "contributor": [
                        self.contributor("marty@example.com"),
                        self.contributor("doc@example.com"),
                    ],
                    "affiliations": [
                        {
                            "uid": "org-uid",
                            "display_names": ["Institut Curie", "Curie"],
                            "type": "institution",
                            "identifiers": [
                                {"harvester": "ror", "value": "04t0gwh46"},
                                {"harvester": "unknown_harvester", "value": "x"},
                            ],
                        }
                    ],
                }
            ],
            "recorded_by": [{"harvester": "hal", "value": "hal-doc-uid"}],
            **kwargs,
        }

    def test_create_document_crisalid_data(self):
        document = self.popu.single(self.document_data())

        document_journal = document.document_journals.get()
        self.assertEqual(document_journal.journal.uid, "journal-uid")
        self.assertEqual(
            document_journal.journal.title, "Journal of Biological Chemistry"
        )
        self.assertEqual(
            (document_journal.volume, document_journal.issue, document_journal.pages),
            ("270", "3", "1-9"),
        )
        organization = document.affiliations.get()
        self.assertEqual(organization.name, "Institut Curie")
        self.assertEqual(
            organization.type, AuthorityOrganization.OrganizationType.INSTITUTION
        )
        # unknown harvesters are ignored
        self.assertEqual(
            list(organization.identifiers.values_list("harvester", flat=True)),
            ["ror"],
        )

    def test_unknown_organization_type(self):
        data = self.document_data()
        data["has_contributions"][0]["affiliations"][0]["type"] = "unknown_type"
        document = self.popu.single(data)
        self.assertEqual(document.affiliations.get().type, "")

    def test_multiple_contributors_in_contribution(self):
        document = self.popu.single(self.document_data())
        self.assertEqual(document.contributors.count(), 2)
        for contributor in DocumentContributor.objects.filter(document=document):
            self.assertEqual(contributor.roles, ["aut"])

    def test_update_document_crisalid_data(self):
        self.popu.single(self.document_data())
        document = self.popu.single(
            self.document_data(publishedInConnection={"edges": []})
        )
        self.assertEqual(Document.objects.count(), 1)
        self.assertFalse(document.document_journals.exists())
        # journal is kept, it can be used by other documents
        self.assertTrue(Journal.objects.filter(uid="journal-uid").exists())

    def test_update_contributors(self):
        self.popu.single(self.document_data())
        data = self.document_data()
        # doc@example.com is removed, marty@example.com has a second contribution
        data["has_contributions"][0]["contributor"].pop()
        data["has_contributions"].append(
            {
                "roles": ["http://id.loc.gov/vocabulary/relators/edt"],
                "contributor": [self.contributor("marty@example.com")],
            }
        )
        document = self.popu.single(data)
        contributor = DocumentContributor.objects.get(document=document)
        self.assertEqual(
            contributor.researcher.identifiers.get(harvester="eppn").value,
            "marty@example.com",
        )
        # roles of all contributions are merged
        self.assertEqual(contributor.roles, ["aut", "edt"])


class TestPopulateStructure(test.TestCase):
    def setUp(self):
        super().setUp()
        self.config = CrisalidConfigFactory()
        self.organization = self.config.organization
        self.root = PeopleGroup.update_or_create_root(self.organization)
        self.popu = PopulateStructure(self.config)

    def test_create_structures(self):
        self.popu.multiple(
            [
                structure_data(
                    "local-LAB",
                    part_of=edges("local-FAC", start_date="2020-01-01"),
                    member_of=edges("local-INSERM", position="main_supervision"),
                    national_type="UMR",
                    types=["OrganizationUnit", "Unit", "ResearchUnit"],
                ),
                structure_data("local-FAC", generic_type="institution_subdivision"),
                structure_data("local-INSERM", generic_type="institution"),
            ]
        )

        lab = Structure.objects.get(crisalid_uid="local-LAB")
        self.assertEqual(lab.organization, self.organization)
        self.assertEqual(lab.name, "long local-LAB")
        self.assertEqual(lab.acronym, "local-LAB")
        self.assertEqual(lab.national_type, "UMR")
        self.assertEqual(lab.main_mission, Structure.MissionType.RESEARCH)
        self.assertEqual(lab.identifiers.get().value, "local-LAB")

        part_of = lab.relations.get(
            relation_type=StructureRelation.RelationType.PART_OF
        )
        self.assertEqual(part_of.related_structure.crisalid_uid, "local-FAC")
        self.assertEqual(part_of.start_date, datetime.date(2020, 1, 1))
        member_of = lab.relations.get(
            relation_type=StructureRelation.RelationType.MEMBER_OF
        )
        self.assertEqual(member_of.related_structure.crisalid_uid, "local-INSERM")
        self.assertEqual(member_of.position, "main_supervision")

        # each structure has a group, all groups in root group (no hierarchy)
        self.assertEqual(group_of("local-LAB").name, "long local-LAB")
        for uid in ("local-LAB", "local-FAC", "local-INSERM"):
            self.assertEqual(group_of(uid).parent, self.root)
        self.assertEqual([s.crisalid_uid for s in lab.parents()], ["local-FAC"])

    def test_populate_idempotent(self):
        datas = [
            structure_data("local-LAB", part_of=edges("local-FAC")),
            structure_data("local-FAC"),
        ]
        self.popu.multiple(datas)
        groups = set(PeopleGroup.objects.values_list("pk", flat=True))

        self.popu.multiple(datas)

        self.assertEqual(Structure.objects.count(), 2)
        self.assertEqual(StructureRelation.objects.count(), 1)
        self.assertEqual(set(PeopleGroup.objects.values_list("pk", flat=True)), groups)

    def test_update_name_and_relations(self):
        self.popu.multiple(
            [
                structure_data("local-LAB", part_of=edges("local-FAC")),
                structure_data("local-FAC"),
            ]
        )
        data = structure_data("local-LAB")
        data["long_labels"] = [{"language": "fr", "value": "new name"}]
        data["descriptions"] = [{"language": "fr", "value": "new description"}]
        self.popu.multiple([data])

        structure = Structure.objects.get(crisalid_uid="local-LAB")
        self.assertEqual(structure.name, "new name")
        self.assertEqual(structure.description, "new description")
        # group is only initialized from the structure
        self.assertEqual(group_of("local-LAB").name, "long local-LAB")
        self.assertFalse(StructureRelation.objects.exists())

    def test_structures_groups_root(self):
        structures_root = PeopleGroupFactory(organization=self.organization)
        self.config.structures_groups_root = structures_root
        self.config.save()
        self.popu.multiple([structure_data("local-LAB")])
        self.assertEqual(group_of("local-LAB").parent, structures_root)

    def test_structures_groups_root_validation(self):
        self.popu.multiple([structure_data("local-LAB")])
        self.config.structures_groups_root = group_of("local-LAB")
        with self.assertRaises(ValidationError):
            self.config.clean()
        self.config.structures_groups_root = PeopleGroupFactory()
        with self.assertRaises(ValidationError):
            self.config.clean()

    def test_create_group_if_missing(self):
        self.popu.multiple([structure_data("local-LAB")])
        group_of("local-LAB").delete()

        self.popu.multiple([structure_data("local-LAB")])

        self.assertIsNotNone(group_of("local-LAB"))

    def test_multiple_parents(self):
        self.popu.multiple(
            [
                structure_data("local-LAB", part_of=edges("local-A", "local-B")),
                structure_data("local-A"),
                structure_data("local-B"),
            ]
        )
        lab = Structure.objects.get(crisalid_uid="local-LAB")
        self.assertEqual(
            {s.crisalid_uid for s in lab.parents()}, {"local-A", "local-B"}
        )

    def test_ended_relation_ignored(self):
        self.popu.multiple(
            [
                structure_data(
                    "local-LAB",
                    part_of={
                        "edges": [
                            *edges("local-A", end_date="2020-01-01")["edges"],
                            *edges("local-B")["edges"],
                        ]
                    },
                ),
                structure_data("local-A"),
                structure_data("local-B"),
            ]
        )
        lab = Structure.objects.get(crisalid_uid="local-LAB")
        self.assertEqual([s.crisalid_uid for s in lab.parents()], ["local-B"])

    def test_hierarchy(self):
        self.popu.multiple(
            [
                structure_data("local-TEAM", part_of=edges("local-LAB")),
                structure_data("local-LAB", part_of=edges("local-FAC")),
                structure_data("local-FAC"),
            ]
        )
        lab = Structure.objects.get(crisalid_uid="local-LAB")
        self.assertEqual([s.crisalid_uid for s in lab.parents()], ["local-FAC"])
        self.assertEqual([s.crisalid_uid for s in lab.children()], ["local-TEAM"])
        fac = Structure.objects.get(crisalid_uid="local-FAC")
        self.assertEqual(
            {s.crisalid_uid for s in fac.descendants()}, {"local-LAB", "local-TEAM"}
        )
        team = Structure.objects.get(crisalid_uid="local-TEAM")
        self.assertEqual(
            {s.crisalid_uid for s in team.ancestors()}, {"local-LAB", "local-FAC"}
        )

    def test_loop_in_hierarchy(self):
        self.popu.multiple(
            [
                structure_data("local-A", part_of=edges("local-B")),
                structure_data("local-B", part_of=edges("local-A")),
            ]
        )
        # relations are saved, walking the hierarchy doesn't loop
        self.assertEqual(StructureRelation.objects.count(), 2)
        structure = Structure.objects.get(crisalid_uid="local-A")
        self.assertEqual([s.crisalid_uid for s in structure.ancestors()], ["local-B"])
        self.assertEqual([s.crisalid_uid for s in structure.descendants()], ["local-B"])

    def test_invalid_structure(self):
        self.assertEqual(
            self.popu.multiple([structure_data("local-X", generic_type="unknown")]),
            [],
        )
        self.assertFalse(Structure.objects.exists())


class TestPopulateResearcherStructures(test.TestCase):
    def setUp(self):
        super().setUp()
        self.config = CrisalidConfigFactory()
        PopulateStructure(self.config).multiple([structure_data("local-LAB")])
        self.structure = Structure.objects.get(crisalid_uid="local-LAB")
        self.popu = PopulateResearcher(self.config)

    def test_membership_creates_group_member(self):
        researcher = self.popu.single(
            researcher_data(
                "marty@example.com",
                memberships=edges("local-LAB", position_code="stat_mmb"),
                employments=edges("local-UNKNOWN"),
            )
        )

        relation = ResearcherStructure.objects.get(researcher=researcher)
        self.assertEqual(relation.structure, self.structure)
        self.assertEqual(relation.position_code, "stat_mmb")
        self.assertIn(researcher.user, self.structure.people_group.members.all())

    def test_membership_periods(self):
        old = edges("local-LAB", start_date="2010-01-01", end_date="2015-01-01")
        current = edges("local-LAB", start_date="2020-01-01", position_code="CR")
        researcher = self.popu.single(
            researcher_data(
                "marty@example.com",
                memberships={"edges": [*old["edges"], *current["edges"]]},
            )
        )

        # all periods are saved, only the current one is active
        relations = ResearcherStructure.objects.filter(researcher=researcher)
        self.assertEqual(relations.count(), 2)
        self.assertEqual([r.position_code for r in relations if r.is_active], ["CR"])
        self.assertIn(researcher.user, self.structure.people_group.members.all())

        # idempotent
        self.popu.single(
            researcher_data(
                "marty@example.com",
                memberships={"edges": [*old["edges"], *current["edges"]]},
            )
        )
        self.assertEqual(relations.count(), 2)

    def test_old_membership(self):
        researcher = self.popu.single(
            researcher_data(
                "marty@example.com",
                memberships=edges(
                    "local-LAB", start_date="2010-01-01", end_date="2015-01-01"
                ),
            )
        )

        # saved, but not member of the group
        self.assertTrue(
            ResearcherStructure.objects.filter(researcher=researcher).exists()
        )
        self.assertNotIn(researcher.user, self.structure.people_group.members.all())

    def test_membership_removed(self):
        self.popu.single(
            researcher_data("marty@example.com", memberships=edges("local-LAB"))
        )
        researcher = self.popu.single(researcher_data("marty@example.com"))

        self.assertFalse(ResearcherStructure.objects.exists())
        self.assertNotIn(researcher.user, self.structure.people_group.members.all())

    def test_sub_structure_members(self):
        PopulateStructure(self.config).multiple(
            [structure_data("local-TEAM", part_of=edges("local-LAB"))]
        )
        team = Structure.objects.get(crisalid_uid="local-TEAM")
        researcher = self.popu.single(
            researcher_data("marty@example.com", employments=edges("local-TEAM"))
        )
        # members of a team are members of its laboratory
        self.assertIn(researcher.user, team.people_group.members.all())
        self.assertIn(researcher.user, self.structure.people_group.members.all())

        # removed from the team, removed from the laboratory
        self.popu.single(researcher_data("marty@example.com"))
        self.assertNotIn(researcher.user, self.structure.people_group.members.all())

    def test_ended_membership(self):
        researcher = self.popu.single(
            researcher_data(
                "marty@example.com",
                memberships=edges("local-LAB", end_date="2020-01-01"),
            )
        )
        self.assertTrue(ResearcherStructure.objects.exists())
        self.assertNotIn(researcher.user, self.structure.people_group.members.all())

    def test_other_roles_kept(self):
        manager = UserFactory()
        self.structure.people_group.managers.add(manager)
        researcher = self.popu.single(
            researcher_data(
                "marty@example.com",
                memberships=edges("local-LAB"),
            )
        )
        self.assertIn(manager, self.structure.people_group.managers.all())
        self.assertIn(researcher.user, self.structure.people_group.members.all())

    def test_document_contributors_keep_memberships(self):
        self.popu.single(
            researcher_data("marty@example.com", memberships=edges("local-LAB"))
        )
        contributor = researcher_data("marty@example.com")
        del contributor["membershipsConnection"]
        del contributor["employmentsConnection"]
        PopulateDocument(self.config).single(
            {
                "publication_date": "2020-01-01",
                "document_type": "Article",
                "titles": [{"language": "en", "value": "title"}],
                "abstracts": [],
                "has_contributions": [{"roles": [], "contributor": [contributor]}],
                "recorded_by": [{"harvester": "hal", "value": "hal-doc"}],
            }
        )
        self.assertTrue(ResearcherStructure.objects.exists())
