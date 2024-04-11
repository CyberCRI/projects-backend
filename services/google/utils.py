from django.conf import settings
from django.db import transaction

from apps.accounts.models import PeopleGroup, ProjectUser

from .models import GoogleAccount, GoogleGroup, GoogleSyncErrors
from .tasks import sync_google_account_groups_task, sync_google_group_members_task


def create_google_account(
    user: ProjectUser, organizational_unit: str = "/CRI/Admin Staff"
):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        google_account, _ = GoogleAccount.objects.update_or_create(
            user=user, defaults={"organizational_unit": organizational_unit}
        )
        google_account, error = google_account.create()
        if not error:
            google_account.create_alias()
            transaction.on_commit(
                lambda: sync_google_account_groups_task.delay(google_account.pk)
            )
        else:
            for task in [
                GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
            ]:
                google_account.update_or_create_error(
                    task, "Error creating google account"
                )


def update_google_account(user: ProjectUser, organizational_unit: str = None):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        google_account = getattr(user, "google_account", None)
        if google_account:
            if organizational_unit:
                google_account.organizational_unit = organizational_unit
                google_account.save()
            google_account.update()
            transaction.on_commit(
                lambda: sync_google_account_groups_task.delay(google_account.pk)
            )


def suspend_google_account(user: ProjectUser):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        google_account = getattr(user, "google_account", None)
        if google_account:
            google_account.suspend()


def create_google_group(people_group: PeopleGroup):
    if people_group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION:
        google_group, _ = GoogleGroup.objects.update_or_create(
            people_group=people_group
        )
        google_group, error = google_group.create()
        if not error:
            google_group.create_alias()
            transaction.on_commit(
                lambda: sync_google_group_members_task.delay(google_group.pk)
            )
        else:
            for task in [
                GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
            ]:
                google_group.update_or_create_error(task, "Error creating google group")


def update_google_group(people_group: PeopleGroup):
    if people_group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION:
        google_group = getattr(people_group, "google_group", None)
        if google_group:
            google_group.update()
            transaction.on_commit(
                lambda: sync_google_group_members_task.delay(google_group.pk)
            )
