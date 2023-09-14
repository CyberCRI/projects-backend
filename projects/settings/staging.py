from celery.schedules import crontab

from projects.settings.base import *  # noqa: F401, F403

ENVIRONMENT = "staging"

FRONTEND_URL = "https://projects.k8s.lp-i.xyz"
PUBLIC_URL = "https://api.projects.k8s.lp-i.xyz"

CELERY_BEAT_SCHEDULE["send_notifications_reminder"] = {  # noqa: F405
    "task": "apps.notifications.tasks.send_notifications_reminder",
    "schedule": crontab(minute="*/5", hour="*"),
}

##############
#   PEOPLE   #
##############

PEOPLE_API_ROOT = "https://pp.api.people.cri-paris.org"

##############
#  MIXPANEL  #
##############

MIXPANEL_PROJECT_ID = "2564648"

##############
#   GOOGLE   #
##############

GOOGLE_EMAIL_PREFIX = "staging"
