from django.conf import settings

from apps.accounts.models import PeopleGroup, ProjectUser
from projects.celery import app
from services.google.interface import GoogleService

from .models import GoogleAccount, GoogleGroup, GoogleSyncErrors


def create_google_account(
    user: ProjectUser, organizational_unit: str = "CRI/Admin Staff"
):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        google_account = GoogleAccount.objects.create(
            user=user, organizational_unit=organizational_unit
        )
        google_account.create()
        google_account.update_keycloak_username()
        create_google_user_task.delay(user.keycloak_id)


def update_google_account(user: ProjectUser, organizational_unit: str = None):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        update_google_user_task.delay(user.keycloak_id, organizational_unit)


def suspend_google_account(user: ProjectUser):
    if user.groups.filter(
        organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
    ).exists():
        suspend_google_user_task.delay(user.keycloak_id)


def create_google_group(people_group: PeopleGroup):
    if people_group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION:
        google_group = GoogleGroup.objects.create(people_group=people_group)
        google_group.create()
        create_google_group_task.delay(people_group.pk)


def update_google_group(people_group: PeopleGroup):
    if people_group.organization.code == settings.GOOGLE_SYNCED_ORGANIZATION:
        update_google_group_task.delay(people_group.pk)


@app.task
def create_google_user_task(user_keycloak_id: str):
    google_account = GoogleAccount.objects.filter(user__keycloak_id=user_keycloak_id)
    if google_account.exists():
        google_account = google_account.get()
        GoogleService.get_user_by_email(google_account.email, 10)
        google_account.create_alias()
        google_account.update_keycloak_username()
        google_account.sync_groups()


@app.task
def update_google_user_task(user_keycloak_id: str, organizational_unit: str = None):
    google_account = GoogleAccount.objects.filter(user__keycloak_id=user_keycloak_id)
    if google_account.exists():
        google_account = google_account.get()
        if organizational_unit:
            google_account.organizational_unit = organizational_unit
            google_account.save()
        google_account.update()
        google_account.sync_groups()


@app.task
def suspend_google_user_task(user_keycloak_id: str):
    google_account = GoogleAccount.objects.filter(user__keycloak_id=user_keycloak_id)
    if google_account.exists():
        google_account = google_account.get()
        google_account.suspend()


@app.task
def create_google_group_task(people_group_id: int):
    google_group = GoogleGroup.objects.filter(people_group__id=people_group_id)
    if google_group.exists():
        google_group = google_group.get()
        google_group.create_alias()
        google_group.sync_members()


@app.task
def update_google_group_task(people_group_id: int):
    google_group = GoogleGroup.objects.filter(people_group__id=people_group_id)
    if google_group.exists():
        google_group = google_group.get()
        google_group.update()
        google_group.sync_members()


@app.task
def retry_failed_tasks():
    failed_tasks = GoogleSyncErrors.objects.filter(solved=False).order_by("created_at")
    for failed_task in failed_tasks:
        failed_task.retry()
