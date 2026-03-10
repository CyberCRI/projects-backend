import json
import math

from django.core.management.base import BaseCommand

from services.crisalid.interface import CrisalidService
from services.crisalid.models import (
    CrisalidConfig,
)
from services.crisalid.utils.timer import timeit


class Command(BaseCommand):
    help = "fetch data from researcher/Document crisalid neo4j/graphql"  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument(
            "organization",
            choices=CrisalidConfig.objects.filter(
                organization__code__isnull=False, active=True
            ).values_list("organization__code", flat=True),
            help="organization code",
        )
        parser.add_argument(
            "command",
            choices=("document", "researcher", "all"),
            help="elements to populate",
        )
        parser.add_argument("--offset", help="offset for graphql", default=0)
        parser.add_argument("--limit", help="limit for graphql", default=100)
        parser.add_argument("--max", help="max loop for graphql", default=math.inf)
        parser.add_argument("--ident", help="indent json output", default=None)
        parser.add_argument("--ouput", help="output directory", default="./")

    def populate_crisalid(
        self,
        service: CrisalidService,
        query: str,
        where: None = None,
        **options,
    ):
        offset = int(options["offset"])
        limit = int(options["limit"])
        max_elements = float(options["max"])
        indent = int(options("indent")) if options("indent") else None
        total = 0

        with timeit(print, f"Populate All Data from '{query}'"):
            while max_elements >= 1:
                with timeit(print, f"GrapQL request {query}"):
                    data = service.query(query, offset=offset, limit=limit, where=where)
                    if not data or not data[query]:
                        break

                total += len(data)

                with open(f"{query}_{offset}.json", "w") as f:
                    json.dump(data, f, indent=indent)

                offset += limit
                max_elements -= 1

    def handle(self, **options):
        config = CrisalidConfig.objects.get(organization__code=options["organization"])
        command = options["command"]

        service = CrisalidService(config)
        if command in ("all", "document"):
            self.populate_crisalid(service, query="documents", **options)

        if command in ("all", "researcher"):
            self.populate_crisalid(
                service,
                query="people",
                # populate only local researcher
                where={"external_EQ": False},
                **options,
            )
