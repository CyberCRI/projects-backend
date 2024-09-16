from django.core.management import BaseCommand

from services.esco.utils import update_esco_data


class Command(BaseCommand):
    """
    Update ESCO data from the ESCO API.

    If the --force-update flag is provided, all data will be updated, even for
    already existing objects. Otherwise, only new objects' data will be updated.
    """

    help = "Update ESCO data from the ESCO API"  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update data for all objects",
        )

    def handle(self, *args, **options):
        update_esco_data(force_update=options.get("force_update", False))
