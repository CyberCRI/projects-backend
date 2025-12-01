import csv

from django.core.management.base import BaseCommand

from services.crisalid.models import Identifier, Researcher


class Command(BaseCommand):
    help = "create csv files for crisalid dag from our researcher"  # noqa: A003

    def handle(self, **options):

        rows = [
            # headers csv
            [
                "first_names",
                "last_name",
                "main_research_structure",
                "tracking_id",
                "eppn",
                "idhal_s",
                "idhal_i",
                "orcid",
                "idref",
                "scopus_eid",
                "institution_identifier",
                "institution_id_nomenclature",
                "position",
                "employment_start_date",
                "employment_end_date",
                "hdr",
            ]
        ]

        # fetch all users with eppn
        for researcher in Researcher.objects.prefetch_related("identifiers").filter(
            identifiers__harvester=Identifier.Harvester.EPPN.value
        ):

            # convert identifiers to a dict key/value
            identifiers = {
                identifier.harvester: identifier.value
                for identifier in researcher.identifiers.all()
            }

            rows.append(
                [
                    # first_names
                    researcher.given_name,
                    # last_name
                    researcher.family_name,
                    # main_research_structure
                    "",
                    # tracking_id
                    identifiers.get(Identifier.Harvester.LOCAL.value, ""),
                    # eppn
                    identifiers.get(Identifier.Harvester.EPPN.value, ""),
                    # idhal_s,
                    "",
                    # idhal_i,
                    "",
                    # orcid
                    identifiers.get(Identifier.Harvester.ORCID.value, ""),
                    # idref
                    identifiers.get(Identifier.Harvester.IDREF.value, ""),
                    # scopus_eid
                    "",
                    # institution_identifier
                    "",
                    # institution_id_nomenclature
                    "",
                    # position
                    "",
                    # employment_start_date
                    "",
                    # employment_end_date
                    "",
                    # hdr
                    "",
                ]
            )

        with open("people.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
