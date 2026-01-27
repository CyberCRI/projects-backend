import math

from django.core.management.base import BaseCommand

from services.crisalid.interface import CrisalidService
from services.crisalid.models import (
    CrisalidConfig,
    Document,
    DocumentContributor,
    Identifier,
    Researcher,
)
from services.crisalid.populates import PopulateDocument, PopulateResearcher
from services.crisalid.populates.base import AbstractPopulate
from services.crisalid.utils.timer import timeit
from services.mistral.models import DocumentEmbedding


class Command(BaseCommand):
    help = "create or update data from researcher/Document crisalid neo4j/graphql"  # noqa: A003

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
            choices=("document", "researcher", "all"),
            help="elements to populate",
        )
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

    def populate_crisalid(
        self,
        service: CrisalidService,
        populate: AbstractPopulate,
        query: str,
        where: None = None,
        **options,
    ):

        offset = int(options["offset"])
        limit = int(options["limit"])
        max_elements = float(options["max"])
        total = 0

        with timeit(print, f"Populate All Data from '{query}'"):

            while max_elements >= 1:

                with timeit(print, f"GrapQL request {query}"):
                    data = service.query(
                        query, offset=offset, limit=limit, where=where
                    )[query]
                    if not data:
                        break

                with timeit(print, "Populate data"):
                    populate.multiple(data)

                total += len(data)
                print(f"{total} done...")

                offset += limit
                max_elements -= 1

    def handle(self, **options):
        config = CrisalidConfig.objects.get(organization__code=options["organization"])
        if options["delete"]:
            self.delete_crisalid_models()

        command = options["command"]
        service = CrisalidService(config)

        if command in ("all", "document"):
            populate = PopulateDocument(config)
            self.populate_crisalid(service, populate, query="documents", **options)

        if command in ("all", "researcher"):
            populate = PopulateResearcher(config)
            self.populate_crisalid(
                service,
                populate,
                query="people",
                # populate only local researcher
                where={"external_EQ": False},
                **options,
            )
