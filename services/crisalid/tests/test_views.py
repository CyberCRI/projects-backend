import datetime

from django import test
from django.urls import reverse

from services.crisalid.models import (
    Document,
    DocumentContributor,
    DocumentTypeCentralized,
    Identifier,
    Researcher,
)

PUBLICATION_TYPE = DocumentTypeCentralized.publications[0]


class TestDocumentView(test.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.researcher = Researcher.objects.create(display_name="james bond")
        cls.researcher_2 = Researcher.objects.create(display_name="ethan hunt")

        cls.researcher.identifiers.add(
            Identifier.objects.create(
                value="hal", harvester=Identifier.Harvester.HAL.value
            )
        )
        cls.researcher_2.identifiers.add(
            Identifier.objects.create(
                value="hal2", harvester=Identifier.Harvester.HAL.value
            )
        )

        # only for researcher 1
        for i in range(10):
            publi = Document.objects.create(
                title=f"title {i}",
                publication_date=datetime.datetime(1990 + i, 1, 1).date(),
                document_type=PUBLICATION_TYPE,
            )
            publi.identifiers.add(
                Identifier.objects.create(
                    value=f"hal-doc 1 {i}",
                    harvester=Identifier.Harvester.HAL.value,
                )
            )
            DocumentContributor.objects.create(
                researcher=cls.researcher, document=publi, roles=["authors"]
            )

        # only for researcher 2
        for i in range(5):
            publi = Document.objects.create(
                title=f"title {i}",
                publication_date=datetime.datetime(1990 + i, 1, 1).date(),
                document_type=PUBLICATION_TYPE,
            )
            publi.identifiers.add(
                Identifier.objects.create(
                    value=f"hal-doc 2 {i}",
                    harvester=Identifier.Harvester.HAL.value,
                )
            )
            DocumentContributor.objects.create(
                researcher=cls.researcher_2, document=publi, roles=["authors"]
            )

        # for both
        for i in range(2):
            publi = Document.objects.create(
                title=f"title {i}",
                publication_date=datetime.datetime(1990 + i, 1, 1).date(),
                document_type=PUBLICATION_TYPE,
            )
            publi.identifiers.add(
                Identifier.objects.create(
                    value=f"hal-doc common {i}",
                    harvester=Identifier.Harvester.HAL.value,
                )
            )
            DocumentContributor.objects.create(
                researcher=cls.researcher, document=publi, roles=["authors"]
            )
            DocumentContributor.objects.create(
                researcher=cls.researcher_2, document=publi, roles=["authors"]
            )

    def test_get_publications(self):
        # researcher 1
        result = self.client.get(
            reverse("ResearcherPublications-list", args=(self.researcher.pk,))
        )

        result = result.json()
        data = result["results"]
        self.assertEqual(len(data), 12)

        # researcher 2
        result = self.client.get(
            reverse("ResearcherPublications-list", args=(self.researcher_2.pk,))
        )

        result = result.json()
        data = result["results"]
        self.assertEqual(len(data), 7)

    def test_get_analytics(self):
        result = self.client.get(
            reverse("ResearcherPublications-analytics", args=(self.researcher.pk,))
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
            reverse("ResearcherPublications-analytics", args=(self.researcher.pk,))
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
