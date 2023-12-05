from datetime import datetime

from django.core.management import BaseCommand
from django.utils.timezone import make_aware

from apps.accounts.models import ProjectUser
from services.keycloak.interface import KeycloakService


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in ProjectUser.objects.all():
            try:
                keycloak_user = KeycloakService.get_user(user.keycloak_id)
                if keycloak_user:
                    user.created_at = make_aware(
                        datetime.fromtimestamp(keycloak_user["createdTimestamp"] / 1000)
                    )
                    user.save()
            except Exception as e:  # noqa
                print(e)
