from datetime import timedelta
from typing import Any, Dict

from django.utils import timezone

from apps.emailing.utils import render_message, send_email
from apps.notifications.models import Notification
from projects.celery import app

from .models import Invitation


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
                "notifications/invitation_reminder_one_week/object",
                "notifications/invitation_reminder_one_week/mail",
                context,
                "week",
            )
        elif start_last_day >= start_of_day and start_end_day <= end_of_day:
            _create_and_send_notification(
                invitation,
                "notifications/invitation_reminder_last_day/object",
                "notifications/invitation_reminder_last_day/mail",
                context,
                "today",
            )
