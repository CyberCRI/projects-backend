from apps.accounts.models import PeopleGroup, ProjectUser
from projects.celery import app

from .models import GoogleAccount, GoogleGroup, GoogleSyncErrors


@app.task
def create_google_user_task(user_keycloal_id: str, organizational_unit: str = "CRI/Admin Staff"):
    return _create_google_user_task(user_keycloal_id, organizational_unit)


@app.task
def update_google_user_task(user_keycloak_id: str, organizational_unit: str = None):
    return _update_google_user_task(user_keycloak_id, organizational_unit)


@app.task
def suspend_google_user_task(user_keycloak_id: str):
    return _suspend_google_user_task(user_keycloak_id)


@app.task
def create_google_group_task(people_group_id: int):
    return _create_google_group_task(people_group_id)


@app.task
def update_google_group_task(people_group_id: int):
    return _update_google_group_task(people_group_id)


def _create_google_user_task(user_keycloal_id: str, organizational_unit: str = "CRI/Admin Staff"):
    user = ProjectUser.objects.get(keycloak_id=user_keycloal_id)
    google_account = GoogleAccount.objects.create(user=user, organizational_unit=organizational_unit)
    google_account.create_process()


def _update_google_user_task(user_keycloak_id: str, organizational_unit: str = None):
    user = ProjectUser.objects.get(keycloak_id=user_keycloak_id)
    if organizational_unit and user.google_account:
        user.google_account.organizational_unit = organizational_unit
        user.google_account.save()
    if user.google_account:
        user.google_account.update_process()


def _suspend_google_user_task(user_keycloak_id: str):
    user = ProjectUser.objects.get(keycloak_id=user_keycloak_id)
    if user.google_account:
        user.google_account.delete_process()


def _create_google_group_task(people_group_id: int):
    people_group = PeopleGroup.objects.get(pk=people_group_id)
    google_group = GoogleGroup.objects.create(people_group=people_group)
    google_group.create_process()


def _update_google_group_task(people_group_id: int):
    people_group = PeopleGroup.objects.get(pk=people_group_id)
    if people_group.google_group:
        people_group.google_group.update_process()
