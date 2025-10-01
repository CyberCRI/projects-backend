import math

from django.core.management.base import BaseCommand

from services.crisalid import populate
from services.crisalid.interface import CrisalidService
from services.crisalid.models import Document, DocumentSource, Identifier, Researcher
from services.crisalid.populate import PopulateDocumentCrisalid


class Command(BaseCommand):
    help = "get data from crisalid neo4j/graphql"

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
        models = [Document, DocumentSource, Identifier, Researcher]

        for model in models:
            deleted = model.objects.all().delete()
            print(f"deleted {model=}: {deleted}")

    def handle(self, **options):
        print(options)
        service = CrisalidService()
        populate = PopulateDocumentCrisalid()

        if options["delete"]:
            self.delete_crisalid_models()

        offset = int(options["offset"])
        limit = int(options["limit"])
        max = float(options["max"])

        while max >= 1:
            data = service.query("document", offset=offset, limit=limit)["documents"]
            if not data:
                break

            populate.multiple(data)

            offset += limit
            max -= 1
