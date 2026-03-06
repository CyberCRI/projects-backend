import json

from django.core.management.base import BaseCommand

from services.crisalid import relators
from services.crisalid.models import Document


class Command(BaseCommand):
    help = "create json files from crisalid for frontend locales"  # noqa: A003

    def handle(self, **options):
        data = {
            "relators": {
                relator["key"]: relator["value"]
                for relator in sorted(relators.raw.values(), key=lambda x: x["key"])
            },
            "document_types": {
                doc.value: str(doc.label)
                for doc in sorted(Document.DocumentType, key=lambda x: x.value)
            },
        }

        with open("researcher.json", "w") as f:
            json.dump(data, f, indent=4)
