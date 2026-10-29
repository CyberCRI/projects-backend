from django.db import models

from apps.commons.mixins import (
    OrganizationRelated,
)


class CrisalidConfig(OrganizationRelated, models.Model):
    """model for crisalid config with host/pass for connected to crisalid,
    is linked to a one organization
    """

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="crisalid",
    )

    crisalidbus_url = models.CharField(
        max_length=255, help_text="crisalidbus/rabimqt host:port"
    )
    crisalidbus_username = models.CharField(
        max_length=255, help_text="crisalidbus/rabimqt username"
    )
    crisalidbus_password = models.CharField(
        max_length=255, help_text="crisalidbus/rabimqt password"
    )

    apollo_url = models.CharField(
        max_length=255, help_text="apollo/graphql host:port/graphql"
    )
    apollo_token = models.CharField(max_length=255, help_text="apollo token")

    active = models.BooleanField(help_text="config is enabled/disabled", default=False)

    def __str__(self):
        active = self.active
        return f"Config: {self.organization} ({active=})"

    def __repr__(self):
        return f"<CrisalidConfig organization={self.organization} active={self.active}>"
