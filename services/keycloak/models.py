from django.db import models

from apps.accounts.models import ProjectUser


class KeycloakAccount(models.Model):
    user = models.OneToOneField(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name="keycloak_account",
    )
    keycloak_id = models.UUIDField(
        auto_created=False, unique=True, help_text="id of user in keycloak"
    )
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True, default="")

    def __str__(self):
        return self.keycloak_id
