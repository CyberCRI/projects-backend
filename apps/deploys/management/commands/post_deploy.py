from django.core.management import BaseCommand

from apps.deploys.models import PostDeployProcess


class Command(BaseCommand):
    def handle(self, *args, **options):
        PostDeployProcess.deploy()
