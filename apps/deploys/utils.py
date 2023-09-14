import logging

from projects.celery import app

logger = logging.getLogger(__name__)


def post_deploy_task(func):
    def wrapper():
        func()

    wrapper.__name__ = func.__name__
    return app.task(wrapper)
