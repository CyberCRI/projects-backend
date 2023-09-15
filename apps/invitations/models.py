import uuid
from typing import TYPE_CHECKING

from django.db import models

from apps.commons.db.abc import HasOwner

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class Invitation(models.Model, HasOwner):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE
    )
    people_group = models.ForeignKey(
        "accounts.PeopleGroup", on_delete=models.CASCADE, null=True
    )
    token = models.UUIDField(default=uuid.uuid4)
    description = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="invitations"
    )
    expire_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.owner == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.owner