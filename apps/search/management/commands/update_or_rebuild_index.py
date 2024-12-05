import subprocess  # nosec B404

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def subprocess_call_command(self, *args):
        return subprocess.run(["python", "manage.py", *args])  # nosec B603, B607

    def handle(self, *args, **options):
        # Update, rebuild or create the index
        try:
            print("Updating index...")
            self.subprocess_call_command("opensearch", "index", "update", "--force")
        except subprocess.CalledProcessError:
            print("Index update failed, rebuilding index...")
            self.subprocess_call_command("opensearch", "index", "rebuild", "--force")

        # Index the data
        self.subprocess_call_command(
            "opensearch", "document", "index", "--force", "--refresh"
        )
