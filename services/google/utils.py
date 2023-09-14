from django.conf import settings

from apps.accounts.models import PeopleGroup, ProjectUser
from services.google.interface import GoogleService


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
            return GoogleService.create_user_process(user, main_group, notify=notify)
        if (
            settings.GOOGLE_EMAIL_DOMAIN in user.email
            or settings.GOOGLE_EMAIL_ALIAS_DOMAIN in user.email
        ):
            if main_group:
                return GoogleService.update_user_process(
                    user, orgUnitPath=f"/CRI/{main_group}"
                )
            return GoogleService.update_user_process(user)
    return user


def suspend_google_account(user: ProjectUser):
    if settings.GOOGLE_SERVICE_ENABLED:
        return GoogleService.suspend_user_process(user)
    return None


def update_or_create_google_group(group: PeopleGroup, create_in_google: bool = False):
    if (
        settings.GOOGLE_SERVICE_ENABLED
        and group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION
    ):
        if create_in_google:
            return GoogleService.create_group_process(group)
        if (
            settings.GOOGLE_EMAIL_DOMAIN in group.email
            or settings.GOOGLE_EMAIL_ALIAS_DOMAIN in group.email
        ):
            return GoogleService.update_group_process(group)
    return group
