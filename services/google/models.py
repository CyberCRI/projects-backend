from django.db import models

from apps.accounts.models import PeopleGroup, ProjectUser


class LPIGoogleAccount(ProjectUser):
    class Meta:
        proxy = True


class LPIGoogleGroup(PeopleGroup):
    class Meta:
        proxy = True


class GoogleSyncErrors(models.Model):
    class OnTaskChoices(models.TextChoices):
        CREATE_USER = "create_user", "Create user"
        UPDATE_USER = "update_user", "Update user"
        SUSPEND_USER = "suspend_user", "Suspend user"
        CREATE_GROUP = "create_group", "Create group"
        UPDATE_GROUP = "update_group", "Update group"

    user = models.ForeignKey(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name="google_sync_errors",
        null=True,
        blank=True,
    )
    people_group = models.ForeignKey(
        PeopleGroup,
        on_delete=models.CASCADE,
        related_name="google_sync_errors",
        null=True,
        blank=True,
    )
    on_task = models.CharField(max_length=50, choices=OnTaskChoices.choices)
    task_kwargs = models.JSONField(null=True, blank=True)
    error = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "google sync error"
        verbose_name_plural = "google sync errors"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} - {self.error}"
