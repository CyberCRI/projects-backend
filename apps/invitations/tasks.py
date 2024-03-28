from datetime import timedelta
from typing import Any, Dict

from django.utils import timezone

from apps.accounts.models import ProjectUser
from apps.emailing.utils import render_message, send_email
from apps.notifications.models import Notification
from projects.celery import app

from .models import AccessRequest, Invitation


@app.task
def send_invitations_reminder():
    _send_invitations_reminder()


def _create_and_send_notification(
    invitation: Invitation,
    subject_path: str,
    mail_path: str,
    context: Dict[str, Any],
    date,
):
    if date == "today":
        Notification.objects.create(
            receiver=invitation.owner,
            type="invitation_today_reminder",
            invitation=invitation,
        )
    else:
        Notification.objects.create(
            receiver=invitation.owner,
            type="invitation_week_reminder",
            invitation=invitation,
        )

    subject, _ = render_message(subject_path, invitation.owner.language)
    text, html = render_message(mail_path, invitation.owner.language, **context)
    send_email(subject, text, [invitation.owner.email], html_content=html)


def _send_invitations_reminder():
    invitations = Invitation.objects.all()
    for invitation in invitations:
        start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        start_last_day = (invitation.expire_at - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start_end_day = start_last_day + timedelta(days=1)
        context = {
            "invitation": invitation,
            "name": invitation.owner.given_name,
        }
        if invitation.expire_at >= start_of_day + timedelta(
            days=7
        ) and invitation.expire_at < end_of_day + timedelta(days=7):
            _create_and_send_notification(
                invitation,
                "invitation_reminder_one_week/object",
                "invitation_reminder_one_week/mail",
                context,
                "week",
            )
        elif start_last_day >= start_of_day and start_end_day <= end_of_day:
            _create_and_send_notification(
                invitation,
                "invitation_reminder_last_day/object",
                "invitation_reminder_last_day/mail",
                context,
                "today",
            )


@app.task
def send_access_request_notification():
    _send_access_request_notification()


def _get_translated_reminder(template_dir, language, **context):
    """
    Return the reminder message in the given language.
    """
    reminder, _ = render_message(f"{template_dir}/reminder", language, **context)
    return reminder


def _create_and_send_notification_for_access_request(
    template_dir: str,
    access_request_nb: int,
    receiver: ProjectUser,
):

    defaults = {
        f"reminder_message_{lang}": _get_translated_reminder(
            template_dir,
            lang,
            count=access_request_nb,
        )
        for lang in ["en", "fr"]
    }
    Notification.objects.create(
        receiver=receiver,
        type="access_request",
        **defaults,
        context={"access_request_nb": access_request_nb},
    )


def _send_access_request_notification():
    access_requests = AccessRequest.objects.all()
    access_requests_list = []
    for access_request in access_requests:
        creation_date = access_request.created_at
        yesterday = timezone.now() - timedelta(days=1)
        if creation_date >= yesterday and access_request.status == "pending":
            access_requests_list.append(access_request)
    org_list = []
    for access_request in access_requests_list:
        if access_request.organization not in org_list:
            org_list.append(access_request.organization)
    for org in org_list:
        pending_access_requests = AccessRequest.objects.filter(
            organization=org, status="pending"
        )
        admins = org.admins.all()
        for admin in admins:
            _create_and_send_notification_for_access_request(
                access_request_nb=len(pending_access_requests),
                receiver=admin,
                template_dir="pending_access_request",
            )
