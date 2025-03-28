from apps.commons.utils import clear_memory
from apps.invitations.models import AccessRequest
from projects.celery import app

from .models import ProjectUser


@app.task(name="apps.accounts.tasks.calculate_users_scores")
@clear_memory
def calculate_users_scores():
    for user in ProjectUser.objects.all():
        user.calculate_score()


@app.task(name="apps.accounts.tasks.send_email_to_user")
@clear_memory
def update_new_user_pending_access_requests(user_pk: int, organization_code: str):
    user = ProjectUser.objects.get(pk=user_pk)
    AccessRequest.objects.filter(
        organization__code=organization_code,
        status=AccessRequest.Status.PENDING,
        user__isnull=True,
        email=user.email,
    ).update(user=user, status=AccessRequest.Status.ACCEPTED)
    AccessRequest.objects.exclude(organization__code=organization_code).filter(
        status=AccessRequest.Status.PENDING,
        user__isnull=True,
        email=user.email,
    ).update(user=user)
