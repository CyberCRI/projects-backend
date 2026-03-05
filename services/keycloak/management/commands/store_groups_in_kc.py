from django.core.management.base import BaseCommand

from apps.accounts.models import ProjectUser
from apps.organizations.models import Organization
from services.keycloak.interface import KeycloakService


class Command(BaseCommand):
    def handle(self, *args, **options):
        for organization in Organization.objects.all():
            KeycloakService.create_organization_group(organization)
        for user in ProjectUser.objects.filter(keycloak_account__isnull=False):
            KeycloakService.set_user_keycloak_groups(user.keycloak_account)
