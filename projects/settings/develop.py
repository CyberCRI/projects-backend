from projects.settings.base import *  # noqa: F401, F403
from projects.settings.base import CELERY_ENABLED

ENVIRONMENT = "develop"

FRONTEND_URL = "https://projects.k8s.lp-i.dev"
PUBLIC_URL = "https://api.projects.k8s.lp-i.dev"

if CELERY_ENABLED:
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE["send_notifications_reminder"] = {  # noqa: F405
        "task": "apps.notifications.tasks.send_notifications_reminder",
        "schedule": crontab(minute="*/5", hour="*"),
    }

##############
#  MIXPANEL  #
##############

MIXPANEL_PROJECT_ID = "2560711"

##############
#   GOOGLE   #
##############

GOOGLE_EMAIL_PREFIX = "develop"
