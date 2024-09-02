from typing import List, Optional

from django.conf import settings

from projects.celery import app

from .utils import send_email


@app.task
def send_email_task(
    subject: str,
    text_content: str,
    to: List[str],
    from_email: str = settings.EMAIL_HOST_USER,
    html_content: Optional[str] = None,
    reply_to: Optional[List[str]] = None,
):
    send_email(subject, text_content, to, from_email, html_content, reply_to)
