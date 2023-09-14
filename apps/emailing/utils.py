import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import translation

logger = logging.getLogger(__name__)


def send_email(
    subject, text_content, to, from_email=settings.EMAIL_HOST_USER, html_content=None
):
    try:
        message = EmailMultiAlternatives(
            subject, text_content, from_email=from_email, to=to
        )
        if html_content is not None:
            message.attach_alternative(html_content, "text/html")
        message.send()
    except smtplib.SMTPException:
        logger.error("Error while sending email", exc_info=True)


def send_email_with_attached_file(
    subject,
    text_content,
    to,
    file,
    file_type,
    from_email=settings.EMAIL_HOST_USER,
    html_content=None,
):
    try:
        message = EmailMultiAlternatives(
            subject, text_content, from_email=from_email, to=to
        )
        message.attach(filename=file.name, content=file.read(), mimetype=file_type)
        if html_content is not None:
            message.attach_alternative(html_content, "text/html")
        message.send()
    except smtplib.SMTPException:
        logger.error("Error while sending email", exc_info=True)


def render_message(template_name: str, language: str = "en", **kwargs):
    """Return the rendered text template and HTML template if it exists.

    A file named '{template_name}.txt' must be present within
    `app/notifications/templates/`. Optionally, an HTML message will be
    generated if a file '{template_name}.html' is present within the same
    directory.

    Templates are rendered using `kwargs` as context.

    Parameters
    ----------
    template_name: str
        Name of the template.
    language: str
        language of the rendered template.
    kwargs: Any:
        Any additional kwargs are given to the template as context.

    Returns
    -------
    Tuple[str, Optional[str]]
        A tuple `(text_content, html_content)` where `text_content` is the
        rendered text and `html_content` the rendered HTML (`None` if no HTML
        template was found).

    Raises
    ------
    TemplateDoesNotExist
        Raised if no text template corresponding to `{template_name}.txt` was
        found.
    """
    kwargs = {
        "public_url": settings.PUBLIC_URL,
        "frontend_url": settings.FRONTEND_URL,
        "email_language": language,
        **kwargs,
    }
    with translation.override(language):
        try:
            text = render_to_string(f"{template_name}.txt", kwargs).strip()
            text = text.replace("&quot;", '"').replace("&#x27;", "'")
        except TemplateDoesNotExist:
            text = ""
        try:
            html = render_to_string(f"{template_name}.html", kwargs).strip()
        except TemplateDoesNotExist:
            html = None
    return text, html
