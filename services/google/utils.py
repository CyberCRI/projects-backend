from django.conf import settings

from apps.accounts.models import PeopleGroup, ProjectUser

from .interface import GoogleService
from .tasks import (
    create_google_group_task,
    create_google_user_taks,
    suspend_google_user_task,
    update_google_group_task,
    update_google_user_task,
)


def update_or_create_google_account(
    user: ProjectUser,
    create_in_google: bool = False,
    main_group: str = "",
    notify: bool = False,
):
    if (
        settings.GOOGLE_SERVICE_ENABLED
        and user.groups.filter(
            organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
        ).exists()
    ):
        if create_in_google:
            google_user = GoogleService.create_user(user, main_group)
            recipients = list(
                set(filter(lambda x: x, [user.email, user.personal_email]))
            )
            user.personal_email = user.email
            user.email = google_user["primaryEmail"]
            user.save()
            create_google_user_taks.delay(user.keycloak_id, notify, recipients)
            return user
        if (
            settings.GOOGLE_EMAIL_DOMAIN in user.email
            or settings.GOOGLE_EMAIL_ALIAS_DOMAIN in user.email
        ):
            if main_group:
                update_google_user_task.delay(
                    user.keycloak_id, orgUnitPath=f"/CRI/{main_group}"
                )
            else:
                update_google_user_task.delay(user.keycloak_id)
    return user


def suspend_google_account(user: ProjectUser):
    if settings.GOOGLE_SERVICE_ENABLED:
        suspend_google_user_task.delay(user.keycloak_id)


def update_or_create_google_group(group: PeopleGroup, create_in_google: bool = False):
    if (
        settings.GOOGLE_SERVICE_ENABLED
        and group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION
    ):
        if create_in_google:
            google_group = GoogleService.create_group(group)
            group.email = google_group["email"]
            group.save()
            create_google_group_task.delay(group.id)
            return group
        if (
            settings.GOOGLE_EMAIL_DOMAIN in group.email
            or settings.GOOGLE_EMAIL_ALIAS_DOMAIN in group.email
        ):
            update_google_group_task.delay(group.id)
    return group
