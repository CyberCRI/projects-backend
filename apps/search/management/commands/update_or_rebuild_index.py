import subprocess  # nosec B404

from django.core.management.base import BaseCommand
from django_opensearch_dsl.registries import registry
from opensearchpy.exceptions import NotFoundError


class Command(BaseCommand):
    def subprocess_call_command(self, *args):
        return subprocess.run(["python", "manage.py", *args])  # nosec B603, B607

    def handle(self, *args, **options):
        """
        Update or create the indices and mappings for all registered models.
        """
        indices = registry.get_indices()
        for index in indices:
            try:
                index.put_mapping(body=index.to_dict()["mappings"])
                self.stdout.write(f"Updated index {index._name}")
            except NotFoundError:
                index.create()
                self.stdout.write(f"Created index {index._name}")
        self.subprocess_call_command(
            "opensearch", "document", "index", "--force", "--refresh"
        )
