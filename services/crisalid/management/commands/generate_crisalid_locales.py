import json
import re

from django.core.management.base import BaseCommand

from services.crisalid.models import Document
from services.crisalid.relators import choices

INVALID_CHAR_REGEX = re.compile(r"[^a-zA-Z0-9-_]")


class Command(BaseCommand):
    help = "create json files from crisalid for frontend locales"  # noqa: A003

    def sanitize_key(self, key: str) -> str:
        """some key are same in it, so replace with -"""

        return INVALID_CHAR_REGEX.sub("-", key).strip("-")

    def handle(self, **options):
        data = {
            "relators": {
                self.sanitize_key(val): val for val in sorted(v for _, v in choices)
            },
            "document_types": {
                self.sanitize_key(val): val
                for val in sorted(doc.value for doc in Document.DocumentType)
            },
        }

        with open("researcher.json", "w") as f:
            json.dump(data, f, indent=4)
