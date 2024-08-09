from celery import Celery

app = Celery("projects")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Set the timezone and enable UTC
app.conf.timezone = "Europe/Paris"
app.conf.enable_utc = True

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
