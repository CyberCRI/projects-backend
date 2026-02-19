from django.core.management.base import BaseCommand

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_default_group
from apps.emailing.utils import render_message, send_email
from apps.organizations.models import Organization
from services.keycloak.exceptions import RemoteKeycloakAccountNotFound
from services.keycloak.interface import KeycloakService


class Command(BaseCommand):
    DIR = "services/keycloak/management/commands"

    def handle_users_in_projects(self):
        organization = Organization.objects.get(code="LEARNINGPLANET")

        csv_file = f"{self.DIR}/users_in_projects.csv"
        users_in_projects = []
        with open(csv_file, "r") as file:
            for line in file:
                keycloak_id = line.strip()
                users_in_projects.append(keycloak_id)

        with open(f"{self.DIR}/users_in_projects_results.csv", "w") as file:
            for keycloak_id in users_in_projects:
                try:
                    try:
                        user = ProjectUser.objects.get(
                            keycloak_account__keycloak_id=keycloak_id
                        )
                    except ProjectUser.DoesNotExist:
                        try:
                            user = ProjectUser.import_from_keycloak(keycloak_id)
                        except RemoteKeycloakAccountNotFound:
                            print(f"{keycloak_id},NOT_FOUND")
                            file.write(f"{keycloak_id},NOT_FOUND\n")
                            continue
                    if user:
                        subject, _ = render_message(
                            "mood_sso_switch/object", user.language, user=user
                        )
                        text, html = render_message(
                            "mood_sso_switch/mail",
                            user.language,
                            user=user,
                            organization=organization,
                        )
                        send_email(subject, text, [user.email], html_content=html)
                        print(f"{keycloak_id},SUCCESS")
                        file.write(f"{keycloak_id},SUCCESS\n")
                    else:
                        print(f"{keycloak_id},NOT_FOUND")
                        file.write(f"{keycloak_id},NOT_FOUND\n")
                except Exception as e:  # noqa: PIE786
                    print(f"{keycloak_id},ERROR,{str(e).replace('\n', ' ')[:120]}")
                    file.write(
                        f"{keycloak_id},ERROR,{str(e).replace('\n', ' ')[:120]}\n"
                    )

    def handle_mood_users_to_create(self):
        default_group = get_default_group()
        organization = Organization.objects.get(code="LEARNINGPLANET")
        people_groups = PeopleGroup.objects.filter(id__in=[])
        people_groups = [people_group.get_members() for people_group in people_groups]
        groups = [default_group, organization.get_users()] + people_groups
        redirect_uri = organization.website_url

        csv_file = f"{self.DIR}/mood_users_to_create.csv"
        mood_users_to_create = []
        with open(csv_file, "r") as file:
            for line in file:
                email, given_name, family_name = line.strip().split(",")
                mood_users_to_create.append(
                    {
                        "email": email,
                        "given_name": given_name,
                        "family_name": family_name,
                    }
                )

        with open(f"{self.DIR}/mood_users_to_create_results.csv", "w") as file:
            for user_data in mood_users_to_create:
                try:
                    user = ProjectUser.objects.create(
                        email=user_data["email"],
                        given_name=user_data["given_name"],
                        family_name=user_data["family_name"],
                    )
                    user.groups.add(*groups)
                    keycloak_account = KeycloakService.create_user(user)
                    link = KeycloakService.get_user_execute_actions_link(
                        keycloak_account,
                        KeycloakService.EmailType.ADMIN_CREATED,
                        ["VERIFY_EMAIL", "UPDATE_PASSWORD"],
                        redirect_uri,
                    )
                    link = KeycloakService.format_execute_action_link_for_template(
                        link, keycloak_account, organization
                    )
                    subject, _ = render_message(
                        "mood_sso_create/object", user.language, user=user
                    )
                    text, html = render_message(
                        "mood_sso_create/mail",
                        user.language,
                        user=user,
                        link=link,
                        organization=organization,
                    )
                    send_email(
                        subject, text, [keycloak_account.email], html_content=html
                    )
                    print(f"{user_data['email']},SUCCESS")
                    file.write(f"{user_data['email']},SUCCESS\n")
                except Exception as e:  # noqa: PIE786
                    print(
                        f"{user_data['email']},ERROR,{str(e).replace('\n', ' ')[:120]}"
                    )
                    file.write(
                        f"{user_data['email']},ERROR,{str(e).replace('\n', ' ')[:120]}\n"
                    )

    def handle_ydc_users_to_create(self):
        default_group = get_default_group()
        organization = Organization.objects.get(code="LEARNINGPLANET")
        people_groups = PeopleGroup.objects.filter(id__in=[])
        people_groups = [people_group.get_members() for people_group in people_groups]
        groups = [default_group, organization.get_users()] + people_groups
        redirect_uri = organization.website_url

        csv_file = f"{self.DIR}/ydc_users_to_create.csv"
        self.ydc_users_to_create = []
        with open(csv_file, "r") as file:
            for line in file:
                email, given_name, family_name = line.strip().split(",")
                self.ydc_users_to_create.append(
                    {
                        "email": email,
                        "given_name": given_name,
                        "family_name": family_name,
                    }
                )

        with open(f"{self.DIR}/ydc_users_to_create_results.csv", "w") as file:
            for user_data in self.ydc_users_to_create:
                try:
                    user = ProjectUser.objects.create(
                        email=user_data["email"],
                        given_name=user_data["given_name"],
                        family_name=user_data["family_name"],
                    )
                    user.groups.add(*groups)
                    keycloak_account = KeycloakService.create_user(user)
                    link = KeycloakService.get_user_execute_actions_link(
                        keycloak_account,
                        KeycloakService.EmailType.ADMIN_CREATED,
                        ["VERIFY_EMAIL", "UPDATE_PASSWORD"],
                        redirect_uri,
                    )
                    link = KeycloakService.format_execute_action_link_for_template(
                        link, keycloak_account, organization
                    )
                    subject, _ = render_message(
                        "mood_sso_create/object", user.language, user=user
                    )
                    text, html = render_message(
                        "mood_sso_create/mail",
                        user.language,
                        user=user,
                        link=link,
                        organization=organization,
                    )
                    send_email(
                        subject, text, [keycloak_account.email], html_content=html
                    )
                    print(f"{user_data['email']},SUCCESS")
                    file.write(f"{user_data['email']},SUCCESS\n")
                except Exception as e:  # noqa: PIE786
                    print(
                        f"{user_data['email']},ERROR,{str(e).replace('\n', ' ')[:120]}"
                    )
                    file.write(
                        f"{user_data['email']},ERROR,{str(e).replace('\n', ' ')[:120]}\n"
                    )

    def handle(self, *args, **options):
        self.handle_users_in_projects()
        self.handle_mood_users_to_create()
        self.handle_ydc_users_to_create()
