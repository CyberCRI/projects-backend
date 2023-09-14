from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, CommandError

from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group


class Command(BaseCommand):
    help = "Add a user identified with it's 'keycloak-id', 'people-id' or 'email' to the superadmin group."  # noqa

    def add_arguments(self, parser):
        parser.add_argument(
            "--keycloak-id", type=str, help="Use a keycloak-id to identify the user."
        )
        parser.add_argument(
            "--people-id", type=str, help="Use a people-id to identify the user."
        )
        parser.add_argument(
            "--email", type=str, help="Use an email address to identify the user."
        )

    def handle(self, *args, **options):
        keycloak_id = options.get("keycloak_id")
        people_id = options.get("people_id")
        email = options.get("email")

        n_identifier = sum(map(bool, [keycloak_id, people_id, email]))
        if n_identifier == 0:
            CommandError(
                "A unique identifier must be given through '--keycloak-id', '--people-id' or '--email'"
            )
        if n_identifier > 1:
            CommandError(
                "Only one of '--keycloak-id', '--people-id' or '--email' must be given."
            )

        try:
            if keycloak_id:
                identifier = "keycloak_id"
                user = ProjectUser.objects.get(keycloak_id=keycloak_id)
            elif people_id:
                identifier = "people_id"
                user = ProjectUser.objects.get(people_id=people_id)
            else:
                identifier = "email"
                user = ProjectUser.objects.get(email=email)
        except (ProjectUser.DoesNotExist, ValidationError):
            raise CommandError(
                f"No user found with '{identifier}={locals()[identifier]}'."
            )

        get_superadmins_group().users.add(user)
        self.stdout.write(
            self.style.SUCCESS(
                f"User '{user}' has sucessfully been added to the superadmin group."
            )
        )
