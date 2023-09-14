import multiprocessing
import os

bind = "0.0.0.0:8000"
accesslog = (
    "-"  # DO NOT REMOVE: This is mandatory for Django to collect Gunicorn's logs
)
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '%(t)s %(h)s %(l)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s ms'
)
max_requests = 1000
max_worker_lifetime = 3600
reload_on_rss = 512
worker_reload_mercy = 60
workers = multiprocessing.cpu_count() * 2 + 1
