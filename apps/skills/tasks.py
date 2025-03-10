from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.commons.utils import clear_memory
from apps.emailing.utils import render_message, send_email
from projects.celery import app

from .models import Mentoring
from .utils import update_esco_data


@clear_memory
@app.task(name="apps.skills.tasks.update_esco_data_task")
def update_esco_data_task():
    update_esco_data()


def _send_mentoring_reminder(inactivity_days: int) -> None:
    """
    Send a reminder to the person contacted for mentoring if no response has been received

    Arguments
    ----------
    inactivity_days : int (3 or 10)
        The number of days since the last message to send the reminder.
        It will also be used to build the template folder name :
            - `reminder_mentoree_3_days`
            - `reminder_mentor_3_days`
            - `reminder_mentoree_10_days`
            - `reminder_mentor_10_days`
    """
    if inactivity_days not in [3, 10]:
        raise ValueError("inactivity_days must be 3 or 10")
    for mentoring in Mentoring.objects.filter(
        (Q(status=Mentoring.MentoringStatus.PENDING) | Q(status__isnull=True))
        & Q(
            messages__created_at__date=(
                timezone.now() - timedelta(days=inactivity_days)
            ).date()
        )
    ).distinct():
        latest_message = mentoring.messages.order_by("-created_at").first()
        if latest_message.created_at.date() == date.today() - timedelta(
            days=inactivity_days
        ):
            if mentoring.mentor == mentoring.created_by:
                receiver = mentoring.mentoree
                template_folder = f"reminder_mentoree_{inactivity_days}_days"
            elif mentoring.mentoree == mentoring.created_by:
                receiver = mentoring.mentor
                template_folder = f"reminder_mentor_{inactivity_days}_days"
            else:
                raise ValueError("Mentoring created_by is not the mentor or mentoree")
            first_message = mentoring.messages.order_by("created_at").first()
            reply_to = receiver.email
            language = receiver.language
            kwargs = {
                "sender": mentoring.created_by,
                "receiver": receiver,
                "skill": getattr(
                    mentoring.skill.tag, f"title_{language}", mentoring.skill.tag.title
                ),
                "organization": mentoring.organization,
                "reply_to": reply_to,
                "content": first_message.content,
            }
            subject, _ = render_message(f"{template_folder}/object", language, **kwargs)
            text, html = render_message(f"{template_folder}/mail", language, **kwargs)
            send_email(
                subject, text, [receiver.email], html_content=html, reply_to=[reply_to]
            )


@app.task(name="apps.skills.tasks.mentoring_reminder")
def mentoring_reminder():
    _send_mentoring_reminder(3)
    _send_mentoring_reminder(10)
