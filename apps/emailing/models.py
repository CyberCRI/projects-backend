import logging
from smtplib import SMTPException
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from apps.emailing.utils import render_message, send_email

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


logger = logging.getLogger(__name__)


class Email(models.Model):
    """
    An Email to send from the Django admin panel
    """

    class EmailTypeChoices(models.TextChoices):
        """
        Send to primary or personal email addresses
        """

        PRIMARY = "primary"
        PERSONAL = "personal"

    class EmailTemplateChoices(models.TextChoices):
        """
        Email templates
        """

        WITH_NAME = "email_with_name"
        WITHOUT_NAME = "email_without_name"

    subject = models.CharField(max_length=255, blank=True, default="")
    content = models.TextField(blank=True, default="")
    images = models.ManyToManyField("files.Image", related_name="emails", blank=True)
    recipients = models.ManyToManyField(
        "accounts.ProjectUser", related_name="+", blank=True
    )
    sent_to = models.ManyToManyField(
        "accounts.ProjectUser", related_name="+", blank=True
    )
    send_to = models.CharField(
        max_length=8,
        choices=EmailTypeChoices.choices,
        default=EmailTypeChoices.PRIMARY.value,
    )
    template = models.CharField(
        max_length=18,
        choices=EmailTemplateChoices.choices,
        default=EmailTemplateChoices.WITH_NAME.value,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def has_been_sent_to_all(self):
        return self.sent_to.count() == self.recipients.count()

    def send(self):
        users_not_sent = self.recipients.exclude(id__in=self.sent_to.all())
        users_sent = []
        for user in users_not_sent:
            try:
                language = user.language
                subject = getattr(self, f"subject_{language}")
                context = {
                    "message": getattr(self, f"content_{language}"),
                    "recipient": user,
                }
                text, html = render_message(
                    f"contact/contact/{self.template}", user.language, **context
                )
                if (
                    self.send_to == self.EmailTypeChoices.PRIMARY
                    or not user.personal_email
                ):
                    send_email(subject, text, [user.email], html_content=html)
                else:
                    send_email(subject, text, [user.personal_email], html_content=html)
                users_sent.append(user)
            except SMTPException as e:
                logger.error(f"Failed to send email to user {user.email} : {e}")
        # add all sended user to the send_to list
        self.sent_to.add(*users_sent)

    def send_test(self, user: "ProjectUser"):
        for language in settings.REQUIRED_LANGUAGES:
            subject = f"[TEST {language}]" + getattr(self, f"subject_{language}")
            context = {
                "message": getattr(self, f"content_{language}"),
                "recipient": user,
            }
            text, html = render_message(
                f"contact/contact/{self.template}", user.language, **context
            )
            if self.send_to == self.EmailTypeChoices.PRIMARY or not user.personal_email:
                send_email(subject, text, [user.email], html_content=html)
            else:
                send_email(subject, text, [user.personal_email], html_content=html)
