import hashlib

from django.core.management import BaseCommand
from django.template.defaultfilters import pluralize

from apps.files import models


class Command(BaseCommand):
    def handle(self, *args, **options):
        updated = 0
        files = models.AttachmentFile.objects.all()
        for file in files:
            if file.hashcode == "":
                hashcode = hashlib.sha256(file.file.read()).hexdigest()
                file.hashcode = hashcode
                file.file.seek(0)  # Reset file position so it starts at 0
                file.save()
                updated += 1
        self.stdout.write(
            f"Process finished, {updated} file{pluralize(updated)} updated."
        )
