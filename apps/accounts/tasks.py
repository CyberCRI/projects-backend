from apps.commons.utils import clear_memory
from apps.invitations.models import AccessRequest
from projects.celery import app

from .models import ProjectUser, UserScore


@app.task(name="apps.accounts.tasks.calculate_users_scores")
@clear_memory
def calculate_users_scores():
    """calculate users scores, get all projectsUser, calculate scores
    next we update all user/score during a bulk_update
    """
    bulk_update: list[UserScore] = []
    bulk_create: list[UserScore] = []

    for user in (
        ProjectUser.objects.select_related("score").prefetch_related("skills").all()
    ):
        user.calculate_score()
        if user.score.pk:
            bulk_update.append(user.score)
        else:
            bulk_create.append(user.score)

    # update or creates scores
    UserScore.objects.bulk_create(bulk_create)
    UserScore.objects.bulk_update(bulk_update, ["score", "completeness", "activity"])


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
