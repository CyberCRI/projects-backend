from typing import TYPE_CHECKING, Any, List, Optional

from django.contrib.auth.models import Group, Permission
from django.db import models
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from guardian.shortcuts import assign_perm, remove_perm

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.organizations.models import Organization
    from apps.projects.models import Project


class Language(models.TextChoices):
    """
    Represent a language, e.g: fr
    """

    FR = "fr", "French"
    EN = "en", "English"

    @classmethod
    def default(cls):
        return Language.EN


class SDG(models.IntegerChoices):
    """
    Represent an SDG by its number.
    See https://www.un.org/sustainabledevelopment
    """

    NO_POVERTY = 1, "No poverty"
    ZERO_HUNGER = 2, "Zero hunger"
    GOOD_HEALTH_AND_WELL_BEING = 3, "Good health and well-being"
    QUALITY_EDUCATION = 4, "Quality education"
    GENDER_EQUALITY = 5, "Gender equality"
    CLEAN_WATER_AND_SANITATION = 6, "Clean water and sanitation"
    AFFORDABLE_AND_CLEAN_ENERGY = 7, "Affordable and clean energy"
    DECENT_WORK_AND_ECONOMIC_GROWTH = 8, "Decent work and economic growth"
    INDUSTRY_INNOVATION_AND_INFRASTRUCTURE = (
        9,
        "Industry, innovation and infrastructure",
    )
    REDUCED_INEQUALITIES = 10, "Reduces inequalities"
    SUSTAINABLE_CITIES_AND_COMMUNITIES = 11, "Sustainable cities and communities"
    RESPONSIBLE_CONSUMPTION_AND_PRODUCTION = 12, "Responsible consumption & production"
    CLIMATE_ACTION = 13, "Climate action"
    LIFE_BELOW_WATER = 14, "Life below water"
    LIFE_ON_LAND = 15, "Life on land"
    PEACE_JUSTICE_AND_STRONG_INSTITUTIONS = 16, "Peace, justice and strong institutions"
    PARTNERSHIPS_FOR_THE_GOALS = 17, "Partnerships for the goals"


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

    def setup_group_object_permissions(
        self, group: Group, permissions: QuerySet[str]
    ) -> Group:
        current_role_permissions = Permission.objects.filter(
            groupobjectpermission__group=group
        )
        permissions_to_remove = current_role_permissions.difference(permissions)
        permissions_to_add = permissions.difference(current_role_permissions)
        for permission in permissions_to_add:
            assign_perm(permission, group, self)
        for permission in permissions_to_remove:
            remove_perm(permission, group, self)
        return group

    def setup_group_global_permissions(
        self, group: Group, permissions: QuerySet[str]
    ) -> Group:
        current_role_permissions = group.permissions.all()
        permissions_to_remove = current_role_permissions.difference(permissions)
        permissions_to_add = permissions.difference(current_role_permissions)
        for permission in permissions_to_add:
            assign_perm(permission, group)
        for permission in permissions_to_remove:
            remove_perm(permission, group)
        return group

    def setup_permissions(
        self, user: Optional["ProjectUser"] = None, trigger_indexation: bool = True
    ):
        """Initialize permissions for the instance."""
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

    def duplicate(self, *args, **kwargs) -> "DuplicableModel":
        raise NotImplementedError()
