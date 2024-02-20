import requests
from celery.schedules import crontab

from projects.settings.base import REQUESTS_DEFAULT_TIMEOUT
from projects.settings.develop import *  # noqa: F401, F403

ENVIRONMENT = "fullstack"

FRONTEND_URL = "https://localhost:8080"
PUBLIC_URL = "http://localhost:8000"

##############
#   CELERY   #
##############

CELERY_BEAT_SCHEDULE = {
    "send_notifications_reminder": {
        "task": "apps.notifications.tasks.send_notifications_reminder",
        "schedule": crontab(minute="*", hour="*"),
    }
}

##############
#   GOOGLE   #
##############

GOOGLE_EMAIL_PREFIX = "fullstack"

##############
#  KEYCLOAK  #
##############

KEYCLOAK_SERVER_URL = "http://keycloak:8080/"
KEYCLOAK_PUBLIC_KEY = requests.get(
    f"{KEYCLOAK_SERVER_URL}realms/lp", timeout=REQUESTS_DEFAULT_TIMEOUT
).json()["public_key"]
KEYCLOAK_PUBLIC_KEY = (
    f"-----BEGIN PUBLIC KEY-----\n{KEYCLOAK_PUBLIC_KEY}\n-----END PUBLIC KEY-----"
)

##############
# SIMPLE_JWT #
##############

# From https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html
SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer", "JWT", "Invite", "Service"),
    "USER_ID_FIELD": "keycloak_account__keycloak_id",
    "USER_ID_CLAIM": "sub",
    "TOKEN_TYPE_CLAIM": "typ",
    "AUTH_TOKEN_CLASSES": ("apps.accounts.authentication.BearerToken",),
    "ALGORITHM": "RS256",
    "VERIFYING_KEY": KEYCLOAK_PUBLIC_KEY,
}
