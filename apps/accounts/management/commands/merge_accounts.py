from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import ProjectUser, Skill
from apps.feedbacks.models import Comment, Follow, Review
from apps.files.models import Image
from apps.notifications.models import Notification, NotificationSettings


class Command(BaseCommand):
    help = "Transfer all data from a user account to another one."  # noqa

    def add_arguments(self, parser):
        parser.add_argument(
            "--old", type=str, help="Use a keycloak-id to identify the old account."
        )
        parser.add_argument(
            "--new", type=str, help="Use a keycloak-id to identify the new account."
        )

    def handle(self, *args, **options):
        old_user_id = options.get("old")
        new_user_id = options.get("new")
        try:
            old_user = ProjectUser.objects.get(keycloak_id=old_user_id)
        except (ProjectUser.DoesNotExist, ValidationError):
            raise CommandError(f"No user found with keycloak_id={old_user_id}.")
        try:
            new_user = ProjectUser.objects.get(keycloak_id=new_user_id)
        except (ProjectUser.DoesNotExist, ValidationError):
            raise CommandError(f"No user found with keycloak_id={new_user_id}.")

        with transaction.atomic():
            new_user.people_id = old_user.people_id
            old_user.people_id = None
            old_user.save()
            new_user.email = old_user.email
            new_user.given_name = old_user.given_name
            new_user.family_name = old_user.family_name
            new_user.birthdate = old_user.birthdate
            new_user.pronouns = old_user.pronouns
            new_user.personal_description = old_user.personal_description
            new_user.short_description = old_user.short_description
            new_user.professional_description = old_user.professional_description
            new_user.location = old_user.location
            new_user.job = old_user.job
            new_user.profile_picture = old_user.profile_picture
            new_user.sdgs = old_user.sdgs
            new_user.facebook = old_user.facebook
            new_user.mobile_phone = old_user.mobile_phone
            new_user.linkedin = old_user.linkedin
            new_user.medium = old_user.medium
            new_user.website = old_user.website
            new_user.personal_email = old_user.personal_email
            new_user.skype = old_user.skype
            new_user.landline_phone = old_user.landline_phone
            new_user.twitter = old_user.twitter
            new_user.people_data = old_user.people_data

            new_user.save()

            # Skills
            Skill.objects.filter(user=old_user).update(user=new_user)

            # Feedbacks
            Comment.objects.filter(author=old_user).update(author=new_user)
            Review.objects.filter(reviewer=old_user).update(reviewer=new_user)
            Follow.objects.filter(follower=old_user).update(follower=new_user)

            # Files
            Image.objects.filter(owner=old_user).update(owner=new_user)

            # Notifications
            new_user.notification_settings.delete()
            Notification.objects.filter(receiver=old_user).update(receiver=new_user)
            NotificationSettings.objects.filter(user=old_user).update(user=new_user)

            # Groups
            new_user.groups.add(*old_user.groups.all())
            old_user.groups.clear()
