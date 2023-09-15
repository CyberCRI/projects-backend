from django.conf import settings
from .models import PostDeployProcess


def deploy(**kwargs):
    environment = settings.ENVIRONMENT
    if environment != "test":
        PostDeployProcess.deploy()
