from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q

from apps.accounts.models import PeopleGroup, ProjectUser
from services.google.interface import GoogleService
from services.google.models import GoogleAccount, GoogleGroup


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Create users
        users = ProjectUser.objects.filter(
            Q(email__icontains=settings.GOOGLE_EMAIL_DOMAIN)
            | Q(email__icontains=settings.GOOGLE_EMAIL_ALIAS_DOMAIN)
        )
        for user in users:
            try:
                google_user = GoogleService.get_user_by_email(user.email, 3)
                if google_user:
                    GoogleAccount.objects.update_or_create(
                        user=user,
                        defaults={
                            "google_id": google_user["id"],
                            "email": google_user["primaryEmail"],
                            "organizational_unit": google_user["orgUnitPath"],
                        },
                    )
                else:
                    print(f"user,{user.email},not found,")
            except Exception as e:  # noqa: PIE786
                print(f"user,{user.email},error,{e}")

        # Create groups
        groups = PeopleGroup.objects.filter(
            Q(email__icontains=settings.GOOGLE_EMAIL_DOMAIN)
            | Q(email__icontains=settings.GOOGLE_EMAIL_ALIAS_DOMAIN)
        )
        for group in groups:
            try:
                google_group = GoogleService.get_group_by_email(group.email, 3)
                if google_group:
                    GoogleGroup.objects.update_or_create(
                        people_group=group,
                        defaults={
                            "google_id": google_group["id"],
                            "email": google_group["email"],
                        },
                    )
                else:
                    print(f"group,{group.email},not found,")
            except Exception as e:  # noqa: PIE786
                print(f"group,{group.email},error,{e}")
