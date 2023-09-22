from typing import Optional

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.emailing.utils import render_message, send_email
from projects.celery import app
from services.keycloak.interface import KeycloakService

from .interface import GoogleService
from .models import GoogleSyncErrors


@app.task
def create_google_user_task(
    user_keycloal_id: str,
    notify: bool = False,
    notify_recipients: Optional[list] = None,
):
    return _create_google_user_task(user_keycloal_id, notify, notify_recipients)


def _create_google_user_task(
    user_keycloal_id: str,
    notify: bool = False,
    notify_recipients: Optional[list] = None,
):
    if not notify_recipients:
        notify_recipients = []
    user = ProjectUser.objects.get(keycloak_id=user_keycloal_id)
    try:
        google_user = GoogleService.get_user(user.email, max_retries=5)
        GoogleService._add_user_alias(google_user)
        GoogleService._sync_user_groups(user, google_user)

        KeycloakService.update_user(user)

        if notify:
            subject, _ = render_message(
                "contact/google_account_created/object", user.language, user=user
            )
            text, html = render_message(
                "contact/google_account_created/mail", user.language, user=user
            )
            send_email(subject, text, notify_recipients, html_content=html)
    except Exception as e:  # noqa
        GoogleSyncErrors.objects.create(
            user=user, on_task=GoogleSyncErrors.OnTaskChoices.CREATE_USER, error=str(e)
        )


@app.task
def update_google_user_task(user_keycloak_id: str, **kwargs):
    return _update_google_user_task(user_keycloak_id, **kwargs)


def _update_google_user_task(user_keycloak_id: str, **kwargs):
    user = ProjectUser.objects.get(keycloak_id=user_keycloak_id)
    try:
        google_user = GoogleService.get_user(user.email)
        if google_user:
            GoogleService._update_user(user, google_user, **kwargs)
            GoogleService._sync_user_groups(user, google_user)
    except Exception as e:  # noqa
        GoogleSyncErrors.objects.create(
            user=user,
            on_task=GoogleSyncErrors.OnTaskChoices.UPDATE_USER,
            error=str(e),
            task_kwargs=kwargs,
        )


@app.task
def suspend_google_user_task(user_keycloak_id: str):
    return _suspend_google_user_task(user_keycloak_id)


def _suspend_google_user_task(user_keycloak_id: str):
    user = ProjectUser.objects.get(keycloak_id=user_keycloak_id)
    try:
        GoogleService.suspend_user(user)
        if user.personal_email:
            subject, _ = render_message(
                "contact/google_account_suspended/object", user.language, user=user
            )
            text, html = render_message(
                "contact/google_account_suspended/mail", user.language, user=user
            )
            send_email(subject, text, [user.personal_email], html_content=html)
    except Exception as e:  # noqa
        GoogleSyncErrors.objects.create(
            user=user, on_task=GoogleSyncErrors.OnTaskChoices.SUSPEND_USER, error=str(e)
        )


@app.task
def create_google_group_task(group_id: int):
    return _create_google_group_task(group_id)


def _create_google_group_task(group_id: int):
    group = PeopleGroup.objects.get(pk=group_id)
    try:
        google_group = GoogleService.get_group(group.email, max_retries=5)
        GoogleService._sync_group_members(group, google_group)
    except Exception as e:  # noqa
        GoogleSyncErrors.objects.create(
            user=group,
            on_task=GoogleSyncErrors.OnTaskChoices.CREATE_GROUP,
            error=str(e),
        )


@app.task
def update_google_group_task(group_id: int):
    return _update_google_group_task(group_id)


def _update_google_group_task(group_id: int):
    group = PeopleGroup.objects.get(pk=group_id)
    try:
        google_group = GoogleService.get_group(group.email)
        if google_group:
            GoogleService._update_group(group, google_group)
            GoogleService._sync_group_members(group, google_group)
    except Exception as e:  # noqa
        GoogleSyncErrors.objects.create(
            user=group,
            on_task=GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP,
            error=str(e),
        )
