from projects.celery import app

from .models import GoogleAccount, GoogleGroup, GoogleSyncErrors


@app.task
def sync_google_account_groups_task(google_account_pk: int):
    google_account = GoogleAccount.objects.filter(pk=google_account_pk)
    if google_account.exists():
        google_account = google_account.get()
        google_account.sync_groups()


@app.task
def sync_google_group_members_task(google_group_pk: int):
    google_group = GoogleGroup.objects.filter(pk=google_group_pk)
    if google_group.exists():
        google_group = google_group.get()
        google_group.sync_members()


@app.task
def retry_failed_tasks():
    failed_tasks = GoogleSyncErrors.objects.filter(solved=False).order_by("created_at")
    for failed_task in failed_tasks:
        failed_task.retry()
