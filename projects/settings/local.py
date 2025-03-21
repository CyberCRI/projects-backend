import os

import requests
from celery.schedules import crontab

from projects.settings.base import *  # noqa: F401, F403
from projects.settings.base import REQUESTS_DEFAULT_TIMEOUT

ENVIRONMENT = "local"

AWS_S3_ENDPOINT_URL = "http://localhost:9000"
AWS_S3_PROXIES = {"http": "http://minio:9000"}

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

FRONTEND_URL = "http://localhost:8080"

SPECTACULAR_SETTINGS["SWAGGER_UI_SETTINGS"]["url"] = "/api/schema/"  # noqa: F405

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

##############
#  MIXPANEL  #
##############

MIXPANEL_PROJECT_ID = "2560711"

##############
#   GOOGLE   #
##############

GOOGLE_EMAIL_PREFIX = os.getenv("GOOGLE_EMAIL_PREFIX", "local")
