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
            "command", choices=("researcher", "all"), help="elements to dumps"
        )
        parser.add_argument("output", help="output path")
        parser.add_argument(
            "--generate-local",
            help="generate local uid",
            default=False,
            action="store_true",
        )

    def csv_researcher(
        self, organization: Organization, output: pathlib.Path, generate_local: bool
    ):
        rows = [
            # headers csv
            [
                "first_names",
                "last_name",
                "main_research_structure",
                "tracking_id",
                "eppn",
                "idhals",
                "idhali",
                "orcid",
                "idref",
                "scopus",
                "institution_identifier",
                "institution_id_nomenclature",
                "position",
                "employment_start_date",
                "employment_end_date",
                "hdr",
            ]
        ]

        local_idx = 0

        # fetch all users with eppn
        for researcher in (
            Researcher.objects.prefetch_related("identifiers")
            .select_related("user")
            .filter(user__groups__in=(organization.get_users(),))
        ):
            # convert identifiers to a dict key/value
            identifiers = {
                identifier.harvester: identifier.value
                for identifier in researcher.identifiers.all()
            }

            local = identifiers.get(Identifier.Harvester.LOCAL.value, "")
            if generate_local:
                local = f"U_{local_idx}"
                local_idx += 1

            eppn = identifiers.get(Identifier.Harvester.EPPN.value, "")
            if not eppn and researcher.user:
                eppn = researcher.user.email

            rows.append(
                [
                    # first_names
                    researcher.given_name,
                    # last_name
                    researcher.family_name,
                    # main_research_structure
                    "",
                    # tracking_id
                    local,
                    # eppn
                    eppn,
                    # idhal_s,
                    identifiers.get(Identifier.Harvester.IDHALS.value, ""),
                    # idhal_i,
                    identifiers.get(Identifier.Harvester.IDHALI.value, ""),
                    # orcid
                    identifiers.get(Identifier.Harvester.ORCID.value, ""),
                    # idref
                    identifiers.get(Identifier.Harvester.IDREF.value, ""),
                    # scopus_eid
                    identifiers.get(Identifier.Harvester.SCOPUS.value, ""),
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

        generate_local = options["generate_local"]

        if command in ("all", "researcher"):
            self.csv_researcher(config.organization, output, generate_local)
