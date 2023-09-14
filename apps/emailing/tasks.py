from django.conf import settings

from projects.celery import app

from .utils import send_email


@app.task
def send_email_task(
    subject, text_content, to, from_email=settings.EMAIL_HOST_USER, html_content=None
):
    send_email(subject, text_content, to, from_email, html_content)
