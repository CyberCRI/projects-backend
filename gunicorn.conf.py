import os

# All of these fields are documented here: https://docs.gunicorn.org/en/stable/settings.html

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
# The Access log file to write to, '-' means log to stdout.
accesslog = "-"
access_log_format = (
    '%(t)s %(h)s %(l)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s ms'
)
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
# Gunicorn concurrent workers, used to handle web requests in parallel
# and allowing continuous service on worker request
workers = os.environ.get("GUNICORN_WORKERS_COUNT", "3")
# Max requests after which a worker is restarted
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
# Random component added to the max_requests to avoid workers to restart at the same time
max_requests_jitter = os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "50")
