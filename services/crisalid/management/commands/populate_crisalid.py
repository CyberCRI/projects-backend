import math

from django.core.management.base import BaseCommand

from services.crisalid.interface import CrisalidService
from services.crisalid.models import (
    Document,
    DocumentContributor,
    Identifier,
    Researcher,
)
from services.crisalid.populates import PopulateDocument
from services.crisalid.utils import timeit
from services.mistral.models import DocumentEmbedding


class Command(BaseCommand):
    help = "create or update data from researcher/Document crisalid neo4j/graphql"  # noqa: A003

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
        models = [
            DocumentEmbedding,
            DocumentContributor,
            Identifier,
            Researcher,
            Document,
        ]

        for model in models:
            deleted = model.objects.all().delete()
            print(f"deleted {model=}: {deleted=}")

    def handle(self, **options):
        if options["delete"]:
            self.delete_crisalid_models()

        service = CrisalidService()
        populate = PopulateDocument()

        offset = int(options["offset"])
        limit = int(options["limit"])
        max_elements = float(options["max"])
        total = 0

        with timeit(print, "Populate All Data"):

            while max_elements >= 1:

                with timeit(print, "GrapQL request "):
                    data = service.query("documents", offset=offset, limit=limit)[
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
