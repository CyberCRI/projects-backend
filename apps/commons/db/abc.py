from typing import TYPE_CHECKING, List, Optional

from django.db import models

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.organizations.models import Organization
    from apps.projects.models import Project


class OrganizationRelated:
    """Abstract class for models related to an `Organization`."""

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        raise NotImplementedError()


class ProjectRelated:
    """Abstract class for models related to `Project`."""

    def get_related_projects(self) -> List["Project"]:
        """Return the projects related to this model."""
        raise NotImplementedError()


class HasOwner:
    """Abstract class for models which have an owner."""

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        raise NotImplementedError()


class PermissionsSetupModel(models.Model):
    """Abstract class for models which should be initialized with permissions."""

    permissions_up_to_date = models.BooleanField(default=False)

    def setup_permissions(self, user: Optional["ProjectUser"] = None):
        """Initialize permissions for the instance."""
        raise NotImplementedError()

    def remove_duplicated_roles(self):
        """Remove duplicated roles in the instance."""
        raise NotImplementedError()

    class Meta:
        abstract = True
