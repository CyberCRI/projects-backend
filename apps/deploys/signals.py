from .models import PostDeployProcess


def deploy(**kwargs):
    PostDeployProcess.deploy()
