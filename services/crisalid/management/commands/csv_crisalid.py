import csv
import pathlib

from django.core.management.base import BaseCommand

from apps.organizations.models import Organization
from services.crisalid.models import CrisalidConfig, Identifier, Researcher


class Command(BaseCommand):
    help = "create csv files for crisalid dag from our researcher"  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument(
            "organization",
            choices=CrisalidConfig.objects.filter(
                organization__code__isnull=False
            ).values_list("organization__code", flat=True),
            help="organization code",
        )
        parser.add_argument(
            "command",
            choices=("researcher", "all"),
            help="elements to dumps",
        )
        parser.add_argument(
            "output",
            default="./",
            help="output path",
        )

    def csv_researcher(self, organization: Organization, output: pathlib.Path):

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
            user__groups__in=(organization.get_users(),)
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

        path = output / "people.csv"
        with path.open("w") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    def handle(self, **options):
        command = options["command"]
        config = CrisalidConfig.objects.get(organization__code=options["organization"])

        output = pathlib.Path(options["output"])

        if command in ("researcher", "all"):
            self.csv_researcher(config, output)
