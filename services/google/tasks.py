from django.conf import settings
from django.db import transaction

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.utils import clear_memory
from projects.celery import app
from services.google.interface import GoogleService

from .models import GoogleAccount, GoogleGroup, GoogleSyncErrors


def create_google_account(
    user: ProjectUser, organizational_unit: str = settings.GOOGLE_DEFAULT_ORG_UNIT
):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        google_account, _ = GoogleAccount.objects.update_or_create(
            user=user, defaults={"organizational_unit": organizational_unit}
        )
        google_account, error = google_account.create()
        if not error:
            transaction.on_commit(lambda: create_google_user_task.delay(user.id))
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
        transaction.on_commit(
            lambda: update_google_user_task.delay(user.id, organizational_unit)
        )


def suspend_google_account(user: ProjectUser):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        suspend_google_user_task.delay(user.id)


def create_google_group(people_group: PeopleGroup):
    if people_group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION:
        google_group, _ = GoogleGroup.objects.update_or_create(
            people_group=people_group
        )
        google_group, error = google_group.create()
        if not error:
            transaction.on_commit(
                lambda: create_google_group_task.delay(people_group.pk)
            )
        else:
            for task in [
                GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
            ]:
                google_group.update_or_create_error(task, "Error creating google group")


def update_google_group(people_group: PeopleGroup):
    if people_group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION:
        transaction.on_commit(lambda: update_google_group_task.delay(people_group.pk))


@app.task(name="services.google.tasks.create_google_user_task")
def create_google_user_task(user_id: str):
    google_account = GoogleAccount.objects.filter(user__id=user_id)
    if google_account.exists():
        google_account = google_account.get()
        GoogleService.get_user_by_email(google_account.email, 10)
        google_account.create_alias()
        google_account.sync_groups()


@app.task(name="services.google.tasks.update_google_user_task")
def update_google_user_task(user_id: str, organizational_unit: str = None):
    google_account = GoogleAccount.objects.filter(user__id=user_id)
    if google_account.exists():
        google_account = google_account.get()
        if organizational_unit:
            google_account.organizational_unit = organizational_unit
            google_account.save()
        google_account.update()
        google_account.sync_groups()


@app.task(name="services.google.tasks.suspend_google_user_task")
def suspend_google_user_task(user_id: str):
    google_account = GoogleAccount.objects.filter(user__id=user_id)
    if google_account.exists():
        google_account = google_account.get()
        google_account.suspend()


@app.task(name="services.google.tasks.create_google_group_task")
def create_google_group_task(people_group_id: int):
    google_group = GoogleGroup.objects.filter(people_group__id=people_group_id)
    if google_group.exists():
        google_group = google_group.get()
        google_group.create_alias()
        google_group.sync_members()


@app.task(name="services.google.tasks.update_google_group_task")
def update_google_group_task(people_group_id: int):
    google_group = GoogleGroup.objects.filter(people_group__id=people_group_id)
    if google_group.exists():
        google_group = google_group.get()
        google_group.update()
        google_group.sync_members()


@clear_memory
@app.task(name="services.google.tasks.retry_failed_tasks")
def retry_failed_tasks():
    failed_tasks = GoogleSyncErrors.objects.filter(solved=False).order_by("created_at")
    for failed_task in failed_tasks:
        failed_task.retry()
