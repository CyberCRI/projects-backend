import datetime
from unittest.mock import patch

from django import test

from apps.accounts.models import PeopleGroup
from services.crisalid.factories import (
    CrisalidConfigFactory,
    DocumentFactory,
    ResearcherFactory,
    faker,
)
from services.crisalid.models import (
    Document,
    DocumentIdentifier,
    Researcher,
    ResearcherIdentifier,
    ResearcherStructure,
    Structure,
)
from services.crisalid.populates import (
    PopulateResearcher,
    PopulateStructure,
)
from services.crisalid.tasks import (
    create_document,
    create_researcher,
    create_structure,
    delete_document,
    delete_researcher,
    delete_structure,
    update_researcher_structures,
)
from services.crisalid.tests.test_populate import (
    edges,
    group_of,
    local_uid,
    researcher_data,
    structure_data,
)


class TestCrisalidTasks(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()
        cls.root = PeopleGroup.update_or_create_root(cls.config.organization)

    def test_delete_document(self):
        document = DocumentFactory()
        document_2 = DocumentFactory()

        fields = {
            "recorded_by": [
                {"harvester": identifier.harvester, "uid": identifier.value}
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
                {"type": identifier.harvester, "value": identifier.value}
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
                {
                    "value": "hals-truc",
                    "harvester": ResearcherIdentifier.Harvester.IDHALS.value,
                }
            ],
        }

        client_gql().execute.return_value = {
            "peopleAggregate": {"count": 1},
            "people": [data],
        }

        create_researcher(self.config.pk, fields)

        # check obj from db
        obj = Researcher.objects.first()

        self.assertEqual(obj.given_name, "marty")
        self.assertEqual(obj.family_name, "mcfly")
        self.assertEqual(obj.identifiers.count(), 1)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, ResearcherIdentifier.Harvester.IDHALS.value)

    @patch("services.crisalid.interface.Client")
    def test_create_document_empty(self, client_gql):
        fields = {"uid": faker.uuid4()}
        client_gql().execute.return_value = {
            "documentsAggregate": {"count": 0},
            "documents": [],
        }

        self.assertEqual(Document.objects.count(), 0)
        create_document(self.config.pk, fields)
        self.assertEqual(Document.objects.count(), 0)

    @patch("services.crisalid.interface.Client")
    def test_create_document(self, client_gql):
        fields = {"uid": faker.uuid4()}
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
                {
                    "harvester": DocumentIdentifier.Harvester.HAL.value,
                    "value": "hals-truc",
                }
            ],
        }

        client_gql().execute.return_value = {
            "documentsAggregate": {"count": 1},
            "documents": [data],
        }

        create_document(self.config.pk, fields)
        # check obj from db
        obj = Document.objects.first()

        self.assertEqual(obj.title, "fiction")
        self.assertEqual(obj.identifiers.count(), 1)
        self.assertEqual(obj.document_type, Document.DocumentType.UNKNOWN.value)
        iden = obj.identifiers.first()
        self.assertEqual(iden.value, "hals-truc")
        self.assertEqual(iden.harvester, DocumentIdentifier.Harvester.HAL.value)

    @patch("services.crisalid.tasks.CrisalidService")
    def test_child_creates_missing_parent(self, service):
        # child is imported before its parent: parent is created (node only)
        PopulateStructure(self.config).multiple(
            [structure_data("local-LAB", part_of=edges("local-FAC"))]
        )
        lab = Structure.objects.get(identifiers__value="local-LAB")
        self.assertEqual([local_uid(s) for s in lab.parents()], ["local-FAC"])
        self.assertEqual(group_of("local-FAC").parent, self.root)

        # parent event: parent is updated, child relation is kept
        service().structure.return_value = structure_data(
            "local-FAC", descriptions=[{"language": "fr", "value": "faculty"}]
        )
        create_structure(self.config.pk, {"uid": "local-FAC"})

        self.assertEqual(
            Structure.objects.get(identifiers__value="local-FAC").description, "faculty"
        )
        self.assertEqual([local_uid(s) for s in lab.parents()], ["local-FAC"])

    def test_delete_structure_deletes_group(self):
        PopulateStructure(self.config).multiple(
            [
                structure_data("local-LAB", part_of=edges("local-FAC")),
                structure_data("local-FAC"),
            ]
        )
        researcher = PopulateResearcher(self.config).single(
            researcher_data("marty@example.com", memberships=edges("local-LAB"))
        )
        fac_group = group_of("local-FAC")
        self.assertIn(researcher.user, fac_group.members.all())
        lab_group = group_of("local-LAB")

        # ikg payload format
        delete_structure(
            self.config.pk,
            {
                "uid": "local-LAB",
                "identifiers": [{"type": "local", "value": "local-LAB"}],
            },
        )

        self.assertFalse(
            Structure.objects.filter(identifiers__value="local-LAB").exists()
        )
        self.assertFalse(PeopleGroup.objects.filter(pk=lab_group.pk).exists())
        # laboratory members are no longer members of the faculty
        self.assertNotIn(researcher.user, fac_group.members.all())

    def test_delete_researcher_syncs_groups(self):
        PopulateStructure(self.config).multiple([structure_data("local-LAB")])
        researcher = PopulateResearcher(self.config).single(
            researcher_data("marty@example.com", memberships=edges("local-LAB"))
        )
        user = researcher.user

        # ikg payload format
        delete_researcher(
            self.config.pk,
            {"identifiers": [{"type": "idhals", "value": "hal-marty@example.com"}]},
        )

        self.assertFalse(ResearcherStructure.objects.exists())
        self.assertNotIn(user, group_of("local-LAB").members.all())


class TestUnchangedPersonEvent(test.TestCase):
    """ikg sends "unchanged" events when only memberships/employments changed"""

    def setUp(self):
        super().setUp()
        self.config = CrisalidConfigFactory()
        PopulateStructure(self.config).multiple(
            [structure_data("local-LAB"), structure_data("local-TEAM")]
        )
        self.researcher = PopulateResearcher(self.config).single(
            researcher_data(
                "marty@example.com",
                memberships=edges("local-LAB", start_date="2020-01-01"),
                employments=edges("local-TEAM", position_code="CR"),
            )
        )

    def fields(self, memberships, employments=None):
        # ikg payload format
        return {
            "uid": "marty@example.com",
            "identifiers": [
                {"type": "eppn", "value": "marty@example.com"},
                {"type": "idhals", "value": "hal-marty@example.com"},
            ],
            "memberships": memberships,
            "employments": employments
            or [
                {
                    "entity_uid": "local-TEAM",
                    "position": {"title": "CR", "code": "CR"},
                    "start_date": None,
                    "end_date": None,
                }
            ],
        }

    @patch("services.crisalid.tasks.CrisalidService")
    def test_relations_changed(self, service):
        fields = self.fields(
            [
                {
                    "entity_uid": "local-LAB",
                    "start_date": "2020-01-01",
                    "end_date": "2024-01-01",
                }
            ]
        )
        service().profile.return_value = researcher_data(
            "marty@example.com",
            memberships=edges(
                "local-LAB", start_date="2020-01-01", end_date="2024-01-01"
            ),
            employments=edges("local-TEAM", position_code="CR"),
        )

        update_researcher_structures(self.config.pk, fields)

        service().profile.assert_called_once()
        membership = ResearcherStructure.objects.get(
            researcher=self.researcher,
            relation_type=ResearcherStructure.RelationType.MEMBERSHIP,
        )
        self.assertEqual(membership.end_date, datetime.date(2024, 1, 1))
        self.assertNotIn(self.researcher.user, group_of("local-LAB").members.all())

    @patch("services.crisalid.tasks.CrisalidService")
    def test_unknown_researcher(self, service):
        fields = self.fields([])
        fields["identifiers"] = [{"type": "idhals", "value": "hal-unknown"}]
        update_researcher_structures(self.config.pk, fields)
        service().profile.assert_not_called()


class TestIdentifiersConfigs(test.TestCase):
    """identifiers are shared by configs: objects are deleted with their last config"""

    def setUp(self):
        super().setUp()
        self.config = CrisalidConfigFactory()
        self.other_config = CrisalidConfigFactory()

    def populate(self, config, data=None):
        return PopulateResearcher(config).single(
            data or researcher_data("marty@example.com")
        )

    def delete_fields(self):
        return {"identifiers": [{"type": "idhals", "value": "hal-marty@example.com"}]}

    def test_populate_links_configs(self):
        researcher = self.populate(self.config)
        self.populate(self.other_config)

        self.assertEqual(Researcher.objects.count(), 1)
        for identifier in researcher.identifiers.all():
            self.assertSetEqual(
                set(identifier.configs.all()), {self.config, self.other_config}
            )

    def test_populate_removed_identifier(self):
        orcid = {"value": "000-666", "harvester": "orcid"}
        data = researcher_data("marty@example.com")
        data["identifiers"].append(orcid)
        researcher = self.populate(self.config, data)
        self.populate(self.other_config)

        # idhals no longer sent by config
        data = researcher_data("marty@example.com")
        data["identifiers"] = [data["identifiers"][0], orcid]
        self.populate(self.config, data)

        idhals = researcher.identifiers.get(harvester="idhals")
        self.assertSetEqual(set(idhals.configs.all()), {self.other_config})
        orcid = researcher.identifiers.get(harvester="orcid")
        self.assertSetEqual(set(orcid.configs.all()), {self.config})

        # orcid is no longer sent by any config
        self.populate(self.config)
        self.assertFalse(researcher.identifiers.filter(harvester="orcid").exists())

    def test_delete_researcher_other_config(self):
        researcher = self.populate(self.config)
        self.populate(self.other_config)

        delete_researcher(self.config.pk, self.delete_fields())

        self.assertTrue(Researcher.objects.filter(pk=researcher.pk).exists())
        for identifier in researcher.identifiers.all():
            self.assertSetEqual(set(identifier.configs.all()), {self.other_config})

        delete_researcher(self.other_config.pk, self.delete_fields())
        self.assertFalse(Researcher.objects.filter(pk=researcher.pk).exists())
        self.assertFalse(ResearcherIdentifier.objects.exists())
