from django.core.management import BaseCommand

from apps.files.tasks import delete_orphan_images


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-t",
            "--threshold",
            type=int,
            help=(
                "Time (in seconds) after which an image is considered an orphan if it was not assigned to any model. "
                "Default to `settings.IMAGE_ORPHAN_THRESHOLD_SECONDS`."
            ),
        )

    def handle(self, *args, **options):
        threshold = options["threshold"]
        if threshold is not None and threshold < 0:
            self.stderr.write("Error: threshold must be a positive integer.")
            exit(1)
        delete_orphan_images(threshold)
