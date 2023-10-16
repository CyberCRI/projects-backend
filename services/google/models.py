from collections.abc import Iterable
from typing import Optional
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.accounts.models import PeopleGroup, ProjectUser
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
    retried_at = models.DateTimeField(auto_now=True)
    retries_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "google sync error"
        verbose_name_plural = "google sync errors"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} - {self.error}"
    
    def retry(self):
        pass


class GoogleGroup(models.Model):
    people_group = models.OneToOneField(
        PeopleGroup,
        on_delete=models.CASCADE,
        related_name="google_group",
        to_field="id",
    )
    google_id = models.CharField(max_length=50, unique=True, null=True)
    email = models.EmailField(unique=True, null=True)

    def __str__(self):
        return self.email

    def create(self) -> "GoogleGroup":
        try:
            google_group = GoogleService.create_group(self.people_group)
            self.email = google_group["email"]
            self.id = google_group["id"]
            self.save()
            self.people_group.email = google_group["email"]
            self.people_group.save()
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                people_group=self.people_group,
                on_task=GoogleSyncErrors.OnTaskChoices.CREATE_GROUP,
                error=e.__traceback__,
            )
        return self

    def update(self):
        try:
            GoogleService.update_group(self)
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                people_group=self.people_group,
                on_task=GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP,
                error=e.__traceback__,
            )

    def create_alias(self):
        try:
            GoogleService.add_group_alias(self)
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                people_group=self.people_group,
                on_task=GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
                error=e.__traceback__,
            )
    
    def sync_members(self):
        try:
            remote_users = [
                google_user["id"] for google_user in GoogleService.get_group_members(self.email)
            ]
            users_to_remove = GoogleAccount.objects.filter(google_id__in=remote_users).exclude(user__groups__people_groups=self.people_group)
            users_to_add = GoogleAccount.objects.filter(user__groups__people_groups=self.people_group).exclude(google_id__in=remote_users)
            
            for user_to_remove in users_to_remove:
                self.remove_member(user_to_remove)
            
            for user_to_add in users_to_add:
                self.add_member(user_to_add)
        
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                people_group=self.people_group,
                on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                error=e.__traceback__,
            )

    def add_member(self, google_user: "GoogleAccount"):
        try:
            GoogleService.add_user_to_group(google_user, self)
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                people_group=self.people_group,
                user=google_user.user,
                on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                error=e.__traceback__,
            )

    def remove_member(self, google_user: "GoogleAccount"):
        try:
            GoogleService.remove_user_from_group(google_user, self)
        except Exception as e:
            GoogleSyncErrors.objects.create(
                people_group=self.people_group,
                user=google_user.user,
                on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                error=e.__traceback__,
            )


class GoogleAccount(models.Model):
    user = models.OneToOneField(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name="google_account",
        to_field="keycloak_id",
    )
    google_id = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True, null=True)
    organizational_unit = models.CharField(max_length=50, null=True)

    def __str__(self):
        return self.email

    def create(self) -> "GoogleAccount":
        try:
            google_user = GoogleService.create_user(self.user, self.organizational_unit)
            self.email = google_user["primaryEmail"]
            self.google_id = google_user["id"]
            self.save()
            self.user.personal_email = self.user.email
            self.user.email = google_user["primaryEmail"]
            self.user.save()
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.CREATE_USER,
                error=e.__traceback__,
            )
        return self
    
    def update(self):
        try:
            GoogleService.update_user(self)
        except Exception as e:
            GoogleSyncErrors.objects.create(
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.UPDATE_USER,
                error=e.__traceback__,
            )
    
    def suspend(self):
        try:
            GoogleService.suspend_user(self)
        except Exception as e:
            GoogleSyncErrors.objects.create(
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.SUSPEND_USER,
                error=e.__traceback__,
            )
    
    def create_alias(self):
        try:
            GoogleService.add_user_alias(self)
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
                error=e.__traceback__,
            )        

    def update_keycloak_username(self):
        try:
            KeycloakService.update_user(self.user)
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
                error=e.__traceback__,
            )
    
    def sync_groups(self):
        try:        
            remote_groups = [
                google_group["id"] for google_group in GoogleService.get_user_groups(self)
            ]
            
            groups_to_remove = GoogleGroup.objects.filter(google_id__in=remote_groups).exclude(people_group__groups__in=self.user.groups.all())
            groups_to_add = GoogleGroup.objects.filter(people_group__groups__users=self.user).exclude(google_id__in=remote_groups)
            
            for group_to_remove in groups_to_remove:
                self.remove_group(group_to_remove)
            
            for group_to_add in groups_to_add:
                self.add_group(group_to_add)
        
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                error=e.__traceback__,
            )

    def add_group(self, google_group: "GoogleGroup"):
        try:
            GoogleService.add_user_to_group(google_group, self)
        except Exception as e:  # noqa
            GoogleSyncErrors.objects.create(
                people_group=google_group.people_group,
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                error=e.__traceback__,
            )

    def remove_group(self, google_group: "GoogleGroup"):
        try:
            GoogleService.remove_user_from_group(google_group, self)
        except Exception as e:
            GoogleSyncErrors.objects.create(
                people_group=google_group.people_group,
                user=self.user,
                on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                error=e.__traceback__,
            )