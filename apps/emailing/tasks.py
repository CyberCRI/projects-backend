from django.conf import settings

from projects.celery import app

from .utils import send_email


@app.task(name="apps.emailing.tasks.send_email_task")
def send_email_task(
    subject: str,
    text_content: str,
    to: list[str],
    from_email: str = settings.EMAIL_HOST_USER,
    html_content: str | None = None,
    reply_to: list[str] | None = None,
    cc: list[str] | None = None,
):
    send_email(subject, text_content, to, from_email, html_content, reply_to, cc)
