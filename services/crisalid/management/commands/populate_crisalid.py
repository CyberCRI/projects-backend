import math

from django.core.management.base import BaseCommand

from services.crisalid.interface import CrisalidService
from services.crisalid.models import Identifier, Publication, Researcher
from services.crisalid.populate import PopulatePublicationCrisalid
from services.crisalid.utils import timeit


class Command(BaseCommand):
    help = "create or update data from researcher/Publication crisalid neo4j/graphql"  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            help="delete all crisalid models",
            default=False,
            action="store_true",
        )
        parser.add_argument("--offset", help="offset for graphql", default=0)
        parser.add_argument("--limit", help="limit for graphql", default=100)
        parser.add_argument("--max", help="max loop for graphql", default=math.inf)

    def delete_crisalid_models(self):
        models = [Publication, Identifier, Researcher]

        for model in models:
            deleted = model.objects.all().delete()
            print(f"deleted {model=}: {deleted}")

    def handle(self, **options):
        service = CrisalidService()
        populate = PopulatePublicationCrisalid()

        if options["delete"]:
            self.delete_crisalid_models()

        offset = int(options["offset"])
        limit = int(options["limit"])
        max_elements = float(options["max"])
        total = 0

        with timeit(print, "Populate All Data"):

            while max_elements >= 1:

                with timeit(print, "GrapQL request "):
                    data = service.query("publications", offset=offset, limit=limit)[
                        "documents"
                    ]
                    if not data:
                        break

                with timeit(print, "Populate data"):
                    populate.multiple(data)

                total += len(data)
                print(f"{total} done...")

                offset += limit
                max_elements -= 1
