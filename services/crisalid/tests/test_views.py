import datetime

from django.urls import reverse
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from services.crisalid.factories import (
    DocumentContributorFactory,
    DocumentFactory,
    ResearcherFactory,
)
from services.crisalid.models import DocumentTypeCentralized

PUBLICATION_TYPE = DocumentTypeCentralized.publications[0]


class TestDocumentView(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.organization = OrganizationFactory()

        cls.researcher = ResearcherFactory()
        cls.researcher_2 = ResearcherFactory()

        grp = cls.organization.get_users()
        cls.researcher.user.groups.add(grp)
        cls.researcher_2.user.groups.add(grp)

        # only for researcher 1
        for i in range(10):
            document = DocumentFactory(
                document_type=PUBLICATION_TYPE,
                publication_date=datetime.datetime(1990 + i, 1, 1).date(),
            )
            DocumentContributorFactory(
                document=document, researcher=cls.researcher, roles=["authors"]
            )

        # only for researcher 2
        for i in range(5):
            document = DocumentFactory(
                document_type=PUBLICATION_TYPE,
                publication_date=datetime.datetime(1990 + i, 1, 1).date(),
            )
            DocumentContributorFactory(
                document=document, researcher=cls.researcher_2, roles=["authors"]
            )

        # for both
        for i in range(2):
            document = DocumentFactory(
                document_type=PUBLICATION_TYPE,
                publication_date=datetime.datetime(1990 + i, 1, 1).date(),
            )
            DocumentContributorFactory(
                document=document, researcher=cls.researcher, roles=["authors"]
            )
            DocumentContributorFactory(
                document=document, researcher=cls.researcher_2, roles=["authors"]
            )

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.researcher.user)

    def test_get_publications(self):
        # researcher 1
        result = self.client.get(
            reverse(
                "ResearcherPublications-list",
                args=(
                    self.organization.code,
                    self.researcher.pk,
                ),
            )
        )

        result = result.json()
        data = result["results"]
        self.assertEqual(len(data), 12)

        # researcher 2
        result = self.client.get(
            reverse(
                "ResearcherPublications-list",
                args=(
                    self.organization.code,
                    self.researcher_2.pk,
                ),
            )
        )

        result = result.json()
        data = result["results"]
        self.assertEqual(len(data), 7)

    def test_get_analytics(self):
        result = self.client.get(
            reverse(
                "ResearcherPublications-analytics",
                args=(
                    self.organization.code,
                    self.researcher.pk,
                ),
            )
        )

        data = result.json()
        expected = {
            "document_types": {PUBLICATION_TYPE: 12},
            "years": [
                {"total": 1, "year": 1999},
                {"total": 1, "year": 1998},
                {"total": 1, "year": 1997},
                {"total": 1, "year": 1996},
                {"total": 1, "year": 1995},
                {"total": 1, "year": 1994},
                {"total": 1, "year": 1993},
                {"total": 1, "year": 1992},
                {"total": 2, "year": 1991},
                {"total": 2, "year": 1990},
            ],
        }
        self.assertEqual(data["document_types"], expected["document_types"])
        self.assertEqual(data["years"], expected["years"])

    def test_get_analytics_limit(self):
        result = self.client.get(
            reverse(
                "ResearcherPublications-analytics",
                args=(
                    self.organization.code,
                    self.researcher.pk,
                ),
            )
            + "?limit=4"
        )

        data = result.json()
        expected = {
            "document_types": {PUBLICATION_TYPE: 12},
            "years": [
                {"total": 1, "year": 1999},
                {"total": 1, "year": 1998},
                {"total": 1, "year": 1997},
                {"total": 1, "year": 1996},
            ],
        }
        self.assertEqual(data["years"], expected["years"])


class TestResearcherView(JwtAPITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organization = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()

        cls.researcher = ResearcherFactory()
        cls.researcher_2 = ResearcherFactory()
        cls.researcher_3 = ResearcherFactory()

        grp = cls.organization.get_users()
        cls.researcher.user.groups.add(grp)
        cls.researcher_2.user.groups.add(grp)

        # other researcher from other organization is not availables
        grp = cls.organization_2.get_users()
        cls.researcher_3.user.groups.add(grp)

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.researcher.user)

    def test_get_list(self):
        response = self.client.get(
            reverse("Researcher-list", args=(self.organization.code,))
        )

        data = response.json()
        researcher_ids = sorted(researcher["id"] for researcher in data["results"])
        expected = sorted((self.researcher.id, self.researcher_2.id))
        self.assertSequenceEqual(researcher_ids, expected)

    def test_get_detail(self):
        response = self.client.get(
            reverse(
                "Researcher-detail",
                args=(
                    self.organization.code,
                    self.researcher.id,
                ),
            )
        )

        researcher = response.json()
        self.assertEqual(researcher["id"], self.researcher.id)

    def test_get_detail_not_know(self):
        response = self.client.get(
            reverse(
                "Researcher-detail",
                args=(
                    self.organization.code,
                    666,
                ),
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_not_found(self):
        response = self.client.get(
            reverse("Researcher-search", args=(self.organization.code,)),
            # data is queryparams
            data={"harvester": "idref", "values": "6666666"},
        )

        data = response.json()
        expected = {}
        self.assertEqual(data["results"], expected)

    def test_not_same_organization(self):
        response = self.client.get(
            reverse("Researcher-search", args=(self.organization_2.code,)),
            # data is queryparams
            data={"harvester": "idref", "values": "6666666"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        expected = {}
        # not same orga, return empty user
        self.assertEqual(results, expected)

    def test_search_found(self):
        identifier = self.researcher.identifiers.first()
        response = self.client.get(
            reverse("Researcher-search", args=(self.organization.code,)),
            # data is queryparams
            data={
                "harvester": identifier.harvester,
                "values": identifier.value,
            },
        )

        data = response.json()
        results = data["results"]

        self.assertEqual(results[identifier.value]["id"], self.researcher.id)

    def test_get_list_not_connected(self):
        self.client.logout()

        response = self.client.get(
            reverse("Researcher-list", args=(self.organization.code,))
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()["results"]
        # 2 user in same organizations
        self.assertEqual(len(results), 2)
