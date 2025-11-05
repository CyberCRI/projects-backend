import json

from django.core.management.base import BaseCommand

from services.crisalid.models import Document
from services.crisalid.relators import choices


class Command(BaseCommand):
    help = "create json files from crisalid for frontend locales"  # noqa: A003

    def handle(self, **options):
        data = {
            "relators": {val: val for val in sorted(v for _, v in choices)},
            "document_types": {
                val: val for val in sorted(doc.value for doc in Document.DocumentType)
            },
        }

        with open("researcher.json", "w") as f:
            json.dump(data, f, indent=4)
