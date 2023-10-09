from django.conf import settings
from apps.accounts.models import PeopleGroup, ProjectUser
from projects.celery import app

from .models import GoogleAccount, GoogleGroup, GoogleSyncErrors


def create_google_account(user: ProjectUser, organizational_unit: str = "CRI/Admin Staff"):
    if user.groups.filter(organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION).exists():
        google_account = GoogleAccount.objects.create(user=user, organizational_unit=organizational_unit)
        google_account.create()
        create_google_user_task.delay(user.keycloak_id, organizational_unit)


def update_google_account(user: ProjectUser, organizational_unit: str = None):
    if user.groups.filter(organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION).exists():
        update_google_user_task.delay(user.keycloak_id, organizational_unit)


def suspend_google_account(user: ProjectUser):
    if user.groups.filter(organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION).exists():
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
def create_google_user_task(user_keycloal_id: str, organizational_unit: str = "CRI/Admin Staff"):
    user = ProjectUser.objects.get(keycloak_id=user_keycloal_id)
    if user.google_account:
        user.google_account.create_alias()
        user.google_account.update_keycloak_username()
        user.google_account.sync_groups()


@app.task
def update_google_user_task(user_keycloak_id: str, organizational_unit: str = None):
    user = ProjectUser.objects.get(keycloak_id=user_keycloak_id)
    if organizational_unit and user.google_account:
        user.google_account.organizational_unit = organizational_unit
        user.google_account.save()
    if user.google_account:
        user.google_account.update()
        user.google_account.sync_groups()


@app.task
def suspend_google_user_task(user_keycloak_id: str):
    user = ProjectUser.objects.get(keycloak_id=user_keycloak_id)
    if user.google_account:
        user.google_account.suspend()


@app.task
def create_google_group_task(people_group_id: int):
    people_group = PeopleGroup.objects.get(pk=people_group_id)
    if people_group.google_group:
        people_group.google_group.create_alias()
        people_group.google_group.sync_members()


@app.task
def update_google_group_task(people_group_id: int):
    people_group = PeopleGroup.objects.get(pk=people_group_id)
    if people_group.google_group:
        people_group.google_group.update()
        people_group.google_group.sync_members()
