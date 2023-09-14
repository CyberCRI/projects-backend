import requests
from celery.schedules import crontab

from projects.settings.base import *  # noqa: F401, F403
from projects.settings.base import REQUESTS_DEFAULT_TIMEOUT

ENVIRONMENT = "local"

DEBUG = True

AWS_S3_ENDPOINT_URL = "http://minio:9000"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

FRONTEND_URL = "http://localhost:8080"

ALGOLIA["AUTO_INDEXING"] = False  # noqa: F405

CELERY_BEAT_SCHEDULE["send_notifications_reminder"] = {  # noqa: F405
    "task": "apps.notifications.tasks.send_notifications_reminder",
    "schedule": crontab(minute="*", hour="*"),
}

##############
#   PEOPLE   #
##############

PEOPLE_API_ROOT = "https://backend.people.k8s.lp-i.dev"

##############
#   RECSYS   #
##############

RECSYS_API_URL = "https://recsys-api.k8s.lp-i.dev"

##############
#  KEYCLOAK  #
##############

KEYCLOAK_SERVER_URL = "http://keycloak:8080"
KEYCLOAK_PUBLIC_KEY = requests.get(
    f"{KEYCLOAK_SERVER_URL}/realms/lp", timeout=REQUESTS_DEFAULT_TIMEOUT
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
    "USER_ID_FIELD": "keycloak_id",
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

GOOGLE_EMAIL_PREFIX = "local"
