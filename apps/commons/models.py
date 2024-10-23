from typing import TYPE_CHECKING, Any, List, Optional

from django.db import models
from django.shortcuts import get_object_or_404

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

    def get_related_project(self) -> Optional["Project"]:
        """Return the projects related to this model."""
        raise NotImplementedError()


class HasOwner:
    """Abstract class for models which have an owner."""

    def get_owner(self):
        """Get the owner of the object."""
        raise NotImplementedError()

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


class HasMultipleIDs:
    """Abstract class for models which have multiple IDs."""

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        raise NotImplementedError()

    @classmethod
    def get_main_id(cls, object_id: Any, returned_field: str = "id") -> Any:
        """Get the main ID from a secondary ID."""
        field_name = cls.get_id_field_name(object_id)
        if field_name == returned_field:
            return object_id
        obj = get_object_or_404(cls, **{field_name: object_id})
        return getattr(obj, returned_field)

    @classmethod
    def get_main_ids(
        cls, objects_ids: List[Any], returned_field: str = "id"
    ) -> List[Any]:
        """Get the main IDs from a list of secondary IDs."""
        return [cls.get_main_id(object_id, returned_field) for object_id in objects_ids]


class DuplicableModel:
    """
    A model that can be duplicated.
    """

    def duplicate(self, *args, **kwargs):
        raise NotImplementedError()
