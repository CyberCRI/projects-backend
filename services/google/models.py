from typing import Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import PeopleGroup, ProjectUser
from services.google.exceptions import GoogleGroupEmailUnavailable, GoogleUserNotSynced
from services.keycloak.interface import KeycloakService

from .interface import GoogleService


class GoogleSyncErrors(models.Model):
    class OnTaskChoices(models.TextChoices):
        CREATE_USER = "create_user", "Create user"
        UPDATE_USER = "update_user", "Update user"
        SUSPEND_USER = "suspend_user", "Suspend user"
        USER_ALIAS = "user_alias", "Create user alias"
        KEYCLOAK_USERNAME = "keycloak_username", "Update keycloak username"
        SYNC_GROUPS = "sync_groups", "Sync user groups"
        CREATE_GROUP = "create_group", "Create group"
        UPDATE_GROUP = "update_group", "Update group"
        GROUP_ALIAS = "group_alias", "Create group alias"
        SYNC_MEMBERS = "sync_members", "Sync group members"

    google_account = models.ForeignKey(
        "google.GoogleAccount",
        on_delete=models.CASCADE,
        related_name="google_sync_errors",
        null=True,
        blank=True,
    )
    google_group = models.ForeignKey(
        "google.GoogleGroup",
        on_delete=models.CASCADE,
        related_name="google_sync_errors",
        null=True,
        blank=True,
    )
    on_task = models.CharField(max_length=50, choices=OnTaskChoices.choices)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    retries_count = models.PositiveIntegerField(default=0)
    solved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "google sync error"
        verbose_name_plural = "google sync errors"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.on_task} google error"

    def retry(self):
        match self.on_task:
            case self.OnTaskChoices.CREATE_USER:
                self.google_account.create(is_retry=True)
            case self.OnTaskChoices.UPDATE_USER:
                self.google_account.update(is_retry=True)
            case self.OnTaskChoices.SUSPEND_USER:
                self.google_account.suspend(is_retry=True)
            case self.OnTaskChoices.USER_ALIAS:
                self.google_account.create_alias(is_retry=True)
            case self.OnTaskChoices.KEYCLOAK_USERNAME:
                self.google_account.update_keycloak_username(is_retry=True)
            case self.OnTaskChoices.SYNC_GROUPS:
                self.google_account.sync_groups(is_retry=True)
            case self.OnTaskChoices.CREATE_GROUP:
                self.google_group.create(is_retry=True)
            case self.OnTaskChoices.UPDATE_GROUP:
                self.google_group.update(is_retry=True)
            case self.OnTaskChoices.GROUP_ALIAS:
                self.google_group.create_alias(is_retry=True)
            case self.OnTaskChoices.SYNC_MEMBERS:
                self.google_group.sync_members(is_retry=True)


class GoogleGroup(models.Model):
    people_group = models.OneToOneField(
        PeopleGroup,
        on_delete=models.CASCADE,
        related_name="google_group",
    )
    google_id = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if (
            self.email != ""
            and GoogleGroup.objects.filter(email=self.email)
            .exclude(people_group=self.people_group)
            .exists()
        ):
            raise ValidationError(
                f"Google group with email {self.email} already exists."
            )
        if (
            self.google_id != ""
            and GoogleGroup.objects.filter(google_id=self.google_id)
            .exclude(people_group=self.people_group)
            .exists()
        ):
            raise ValidationError(
                f"Google group with id {self.google_id} already exists."
            )
        return super().save(*args, **kwargs)

    def update_or_create_error(
        self,
        on_task: str,
        error: Optional[Exception] = None,
        google_account: Optional["GoogleAccount"] = None,
    ):
        defaults = {"solved": error is None}
        if error is not None:
            defaults["error"] = str(error)
        error, created = GoogleSyncErrors.objects.update_or_create(
            google_group=self,
            google_account=google_account,
            on_task=on_task,
            solved=False,
            defaults=defaults,
        )
        if not created:
            error.retries_count += 1
            error.save()

    def create(
        self, is_retry: bool = False
    ) -> Tuple["GoogleGroup", Optional[Exception]]:
        try:
            google_group = GoogleService.create_group(self.people_group)
            self.email = google_group["email"]
            self.google_id = google_group["id"]
            self.save()
            self.people_group.email = google_group["email"]
            self.people_group.save()
        except GoogleGroupEmailUnavailable as e:
            raise e
        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.CREATE_GROUP, e)
            return self, e
        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.CREATE_GROUP)
        return self, None

    def update(self, is_retry: bool = False):
        try:
            GoogleService.update_group(self)
        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP, e)
        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP)

    def create_alias(self, is_retry: bool = False):
        try:
            GoogleService.add_group_alias(self)
        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS, e)
        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS)

    def sync_members(self, is_retry: bool = False):
        try:
            remote_users = [
                google_user["id"]
                for google_user in GoogleService.get_group_members(self)
            ]
            users_to_remove = GoogleAccount.objects.filter(
                google_id__in=remote_users
            ).exclude(user__groups__people_groups=self.people_group)
            users_to_add = GoogleAccount.objects.filter(
                user__groups__people_groups=self.people_group
            ).exclude(google_id__in=remote_users)

            for user_to_remove in users_to_remove:
                self.remove_member(user_to_remove, is_retry=is_retry)

            for user_to_add in users_to_add:
                self.add_member(user_to_add, is_retry=is_retry)

        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS, e)
        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS)

    def add_member(self, google_user: "GoogleAccount", is_retry: bool = False):
        try:
            GoogleService.add_user_to_group(google_user, self)
        except Exception as e:  # noqa
            self.update_or_create_error(
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS, e, google_user
            )
        else:
            if is_retry:
                self.update_or_create_error(
                    GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                    google_account=google_user,
                )

    def remove_member(self, google_user: "GoogleAccount", is_retry: bool = False):
        try:
            GoogleService.remove_user_from_group(google_user, self)
        except Exception as e:  # noqa
            self.update_or_create_error(
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS, e, google_user
            )
        else:
            if is_retry:
                self.update_or_create_error(
                    GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                    google_account=google_user,
                )


class GoogleAccount(models.Model):
    user = models.OneToOneField(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name="google_account",
    )
    google_id = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    organizational_unit = models.CharField(max_length=50, default="/CRI/Admin Staff")

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if (
            self.email != ""
            and GoogleAccount.objects.filter(email=self.email)
            .exclude(user=self.user)
            .exists()
        ):
            raise ValidationError(
                f"Google account with email {self.email} already exists."
            )
        if (
            self.google_id != ""
            and GoogleAccount.objects.filter(google_id=self.google_id)
            .exclude(user=self.user)
            .exists()
        ):
            raise ValidationError(
                f"Google account with id {self.google_id} already exists."
            )
        return super().save(*args, **kwargs)

    def update_or_create_error(
        self,
        on_task: str,
        error: Optional[Exception] = None,
        google_group: Optional["GoogleGroup"] = None,
    ):
        defaults = {"solved": error is None}
        if error is not None:
            defaults["error"] = error
        error, created = GoogleSyncErrors.objects.update_or_create(
            google_group=google_group,
            google_account=self,
            on_task=on_task,
            solved=False,
            defaults=defaults,
        )
        if not created:
            error.retries_count += 1
            error.save()

    def create(
        self, is_retry: bool = False
    ) -> Tuple["GoogleAccount", Optional[Exception]]:
        try:
            google_user = GoogleService.create_user(self.user, self.organizational_unit)
            self.email = google_user["primaryEmail"]
            self.google_id = google_user["id"]
            self.save()
            self.user.personal_email = self.user.email
            self.user.email = google_user["primaryEmail"]
            self.user.save()
        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.CREATE_USER, e)
            return self, e
        if is_retry:
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.CREATE_USER)
        return self, None

    def update(self, is_retry: bool = False):
        try:
            GoogleService.update_user(self)
        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.UPDATE_USER, e)
        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.UPDATE_USER)

    def suspend(self, is_retry: bool = False):
        try:
            GoogleService.suspend_user(self)
        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.SUSPEND_USER, e)
        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.SUSPEND_USER)

    def create_alias(self, is_retry: bool = False):
        try:
            GoogleService.add_user_alias(self)
        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.USER_ALIAS, e)
        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.USER_ALIAS)

    def update_keycloak_username(self, is_retry: bool = False):
        try:
            if self.user.email == self.email:
                KeycloakService.update_user(self.user)
            else:
                self.update_or_create_error(
                    GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
                    GoogleUserNotSynced(self.user.email, self.email),
                )
        except Exception as e:  # noqa
            self.update_or_create_error(
                GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME, e
            )
        else:
            if is_retry:
                self.update_or_create_error(
                    GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME
                )

    def sync_groups(self, is_retry: bool = False):
        try:
            remote_groups = [
                google_group["id"]
                for google_group in GoogleService.get_user_groups(self)
            ]

            groups_to_remove = GoogleGroup.objects.filter(
                google_id__in=remote_groups
            ).exclude(people_group__groups__in=self.user.groups.all())
            groups_to_add = GoogleGroup.objects.filter(
                people_group__groups__users=self.user
            ).exclude(google_id__in=remote_groups)

            for group_to_remove in groups_to_remove:
                self.remove_group(group_to_remove, is_retry=is_retry)

            for group_to_add in groups_to_add:
                self.add_group(group_to_add, is_retry=is_retry)

        except Exception as e:  # noqa
            self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS, e)

        else:
            if is_retry:
                self.update_or_create_error(GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS)

    def add_group(self, google_group: "GoogleGroup", is_retry: bool = False):
        try:
            GoogleService.add_user_to_group(self, google_group)
        except Exception as e:  # noqa
            self.update_or_create_error(
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS, e, google_group
            )
        else:
            if is_retry:
                self.update_or_create_error(
                    GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                    google_group=google_group,
                )

    def remove_group(self, google_group: "GoogleGroup", is_retry: bool = False):
        try:
            GoogleService.remove_user_from_group(self, google_group)
        except Exception as e:  # noqa
            self.update_or_create_error(
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS, e, google_group
            )
        else:
            if is_retry:
                self.update_or_create_error(
                    GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                    google_group=google_group,
                )
