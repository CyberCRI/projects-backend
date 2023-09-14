from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_frontend_url():
    return settings.FRONTEND_URL
