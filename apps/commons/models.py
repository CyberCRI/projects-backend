from typing import List, Optional

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import models


class GroupData(models.Model):
    """
    Additional data for a django.contrib.auth.models.Group instance.

    Attributes:
    ----------
        group: ForeignKey
            The related group.
        content_type: ForeignKey
            The content type of the related instance.
        object_id: CharField
            The ID of the related instance.
        role: CharField
    """

    class Role(models.TextChoices):
        # Base roles
        SUPERADMINS = "superadmins"
        DEFAULT = "default"
        # Project roles
        REVIEWERS = "reviewers"
        OWNERS = "owners"
        REVIEWER_GROUPS = "reviewer_groups"
        OWNER_GROUPS = "owner_groups"
        MEMBER_GROUPS = "member_groups"
        # People group roles
        LEADERS = "leaders"
        MANAGERS = "managers"
        # Project + people group roles
        MEMBERS = "members"
        # Organization roles
        ADMINS = "admins"
        FACILITATORS = "facilitators"
        USERS = "users"
        VIEWERS = "viewers"

    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="data")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.CharField(max_length=255, null=True)
    role = models.CharField(max_length=255, choices=Role.choices)

    def __str__(self) -> str:
        return f"{self.group} - {self.role}"

    @property
    def instance(self) -> Optional[models.Model]:
        """Return the related instance."""
        if self.content_type:
            obj = self.content_type.get_object_for_this_type(pk=self.object_id)
            if not hasattr(obj, "deleted_at") or not obj.deleted_at:
                return obj
        return None

    @classmethod
    def project_roles(cls) -> List[str]:
        return [
            cls.Role.REVIEWERS,
            cls.Role.OWNERS,
            cls.Role.MEMBERS,
            cls.Role.REVIEWER_GROUPS,
            cls.Role.OWNER_GROUPS,
            cls.Role.MEMBER_GROUPS,
        ]

    @classmethod
    def people_group_roles(cls) -> List[str]:
        return [
            cls.Role.LEADERS,
            cls.Role.MANAGERS,
            cls.Role.MEMBERS,
        ]

    @classmethod
    def organization_roles(cls) -> List[str]:
        return [
            cls.Role.ADMINS,
            cls.Role.FACILITATORS,
            cls.Role.USERS,
            cls.Role.VIEWERS,
        ]
