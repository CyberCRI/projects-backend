from typing import TYPE_CHECKING, Any, Dict, List, Optional

from django.contrib.auth.models import Group, Permission
from django.db.models import Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from guardian.shortcuts import assign_perm, remove_perm

from .models import GroupData

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.organizations.models import Organization
    from apps.projects.models import Project


class OrganizationRelated:
    """Abstract class for models related to an `Organization`."""

    organization_query_string: str = "organization"

    @classmethod
    def organization_query(cls, key: str, value: Any) -> Q:
        """Return the query string to use to filter by organization."""
        if not key and not cls.organization_query_string:
            raise ValueError(
                "You cannot query without a key or organization_query_string."
            )
        if cls.organization_query_string and key:
            return Q(**{f"{cls.organization_query_string}__{key}": value})
        if cls.organization_query_string:
            return Q(**{cls.organization_query_string: value})
        return Q(**{key: value})

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        raise NotImplementedError()


class ProjectRelated(OrganizationRelated):
    """
    Abstract class for models related to `Project`.
    This class extends `OrganizationRelated` because projects are OrganizationRelated
    themselves, so any model related to a project is also related to one or more
    organizations.

    For MRO consistency, this class must come before `OrganizationRelated` in the
    inheritance order:

    ```
    class MyModel(..., ProjectRelated, OrganizationRelated, ...):
        ...
    ```

    Most of the time, it is not necessary to use both mixins, but for some models it is
    better to explicitly state both relations, as the relation to the organization might
    exist outside of the relation to the project.
    """

    organization_query_string: str = "project__organizations"
    project_query_string: str = "project"

    @classmethod
    def project_query(cls, key: str, value: Any) -> Q:
        """Return the query string to use to filter by project."""
        if not key and not cls.project_query_string:
            raise ValueError("You cannot query without a key or project_query_string.")
        if cls.project_query_string and key:
            return Q(**{f"{cls.project_query_string}__{key}": value})
        if cls.project_query_string:
            return Q(**{cls.project_query_string: value})
        return Q(**{key: value})

    @classmethod
    def organization_query(cls, key: str, value: Any) -> Q:
        """Return the query string to use to filter by organization."""
        if not key and not cls.organization_query_string:
            raise ValueError(
                "You cannot query without a key or organization_query_string."
            )
        if cls.organization_query_string and key:
            return Q(**{f"{cls.organization_query_string}__{key}": value})
        if cls.organization_query_string:
            return Q(**{cls.organization_query_string: value})
        return Q(**{key: value})

    def get_related_project(self) -> Optional["Project"]:
        """Return the projects related to this model."""
        raise NotImplementedError()

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        raise NotImplementedError()


class HasOwner:
    """Abstract class for models which have an owner."""

    def get_owner(self):
        """Get the owner of the object."""
        raise NotImplementedError()

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        raise NotImplementedError()


class HasOwners:
    """Abstract class for models which have an owner."""

    def get_owners(self):
        """Get the owner of the object."""
        raise NotImplementedError()

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        raise NotImplementedError()


class HasPermissionsSetup:
    """
    This mixin handles models that have permissions on the instance level.

    Models based on this mixin must implement a `permissions_up_to_date` field to store
    that is used to check if all the instances permissions have been updated after a
    potential change.

    The model must also override the `setup_permissions` method that assigns the
    instances' permissions.
    """

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

    def get_or_create_group(self, name: str) -> Group:
        """Return the group with the given name."""
        group, created = Group.objects.get_or_create(
            name=f"{self.content_type.model}:#{self.pk}:{name}"
        )
        if created:
            self.groups.add(group)
        if not group.data.exists():
            GroupData.objects.update_or_create(
                group=group,
                defaults={
                    "role": name,
                    "content_type": self.content_type,
                    "object_id": self.pk,
                },
            )
        return group

    def setup_permissions(
        self, user: Optional["ProjectUser"] = None, trigger_indexation: bool = True
    ):
        """Initialize permissions for the instance."""
        raise NotImplementedError()


class DuplicableModel:
    """
    A model that can be duplicated.
    """

    def duplicate(self, *args, **kwargs) -> "DuplicableModel":
        raise NotImplementedError()


class HasMultipleIDs:
    """
    This mixin handles models with multiple identifiers, including slugs.

    Models based on this mixin must implement a `slug` field to store the current slug
    and an `outdated_slugs` field to store the previous slugs. The `slugified_fields`
    attribute must be defined to specify which fields are used to generate the slug.
    If any of these fields is modified, the slug will be updated.

    The model must also override the `get_id_field_name` method that returns the name
    of the id field based on checks that can detect what type of identifier is passed.

    Because this mixin overrides the `save` method it must come after `models.Model`
    in the inheritance order.

    Example
    ------
    ```
    class ModelWithSlug(HasMultipleIDs, models.Model):
        slugified_fields: List[str] = ["field_used_for_slug"]
        slug_prefix: str = "my-model"
        slug = models.SlugField(unique=True)
        outdated_slugs = ArrayField(models.SlugField(), default=list)

        @classmethod
        def get_id_field_name(cls, object_id: Any) -> str:
            if isinstance(object_id, int):
                return "id"
            return "slug"
    ```

    Attributes
    ------
    slugified_fields: List[str]
        The fields that are used to generate the slug. If any of these fields
        is modified, the slug will be updated.
    slug_prefix: str
        The prefix to add to the slug if there is a potential clash with another
        identifier.

    Model Fields
    ------
    slug: SlugField
        The current slug of the object.
    outdated_slugs: ArrayField(SlugField)
        The outdated slugs of the object. They are kept for url retro-compatibility.
    """

    _original_slug_fields_value: Dict[str, str] = {}
    slugified_fields: List[str] = []
    reserved_slugs: List[str] = []
    slug_prefix: str = ""

    def __init__(self, *args, **kwargs):
        self._original_slug_fields_value = {
            field: getattr(self, field, "") for field in self.slugified_fields
        }
        super(HasMultipleIDs, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.slug or any(
            getattr(self, field) != self._original_slug_fields_value[field]
            for field in self.slugified_fields
        ):
            new_slug = self.get_slug()
            if (
                self.slug
                and new_slug != self.slug
                and self.slug not in self.outdated_slugs
            ):
                self.outdated_slugs = self.outdated_slugs + [self.slug]
            self.slug = new_slug
            self._original_slug_fields_value = {
                field: getattr(self, field, "") for field in self.slugified_fields
            }
        return super().save(*args, **kwargs)

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
        try:
            obj = get_object_or_404(cls, **{field_name: object_id})
        except Http404 as e:
            if field_name == "slug":
                obj = get_object_or_404(cls, outdated_slugs__contains=[object_id])
            else:
                raise e
        return getattr(obj, returned_field)

    @classmethod
    def get_main_ids(
        cls, objects_ids: List[Any], returned_field: str = "id"
    ) -> List[Any]:
        """Get the main IDs from a list of secondary IDs."""
        return [cls.get_main_id(object_id, returned_field) for object_id in objects_ids]

    @classmethod
    def slug_exists(cls, slug: str) -> bool:
        # Handle soft-deleted objects
        if hasattr(cls.objects, "all_with_delete"):
            objects = cls.objects.all_with_delete()
        else:
            objects = cls.objects.all()
        return objects.filter(
            Q(slug=slug) | Q(outdated_slugs__contains=[slug])
        ).exists()

    def get_slug(self) -> str:
        raw_slug = [getattr(self, field) for field in self.slugified_fields]
        raw_slug = slugify("-".join(raw_slug)[0:46])
        if not raw_slug or raw_slug == "-":
            raw_slug = self.slug_prefix
        # If there is a potential clash with another identifier, add the prefix
        while self.get_id_field_name(raw_slug) != "slug":
            raw_slug = f"{self.slug_prefix}-{raw_slug}"
        same_slug_count = 0
        slug = raw_slug
        while self.slug_exists(slug) or slug in [
            self.slug_prefix,
            *self.reserved_slugs,
        ]:
            if slug in self.outdated_slugs or slug == self.slug:
                return slug
            same_slug_count += 1
            slug = f"{raw_slug}-{same_slug_count}"
            if self.get_id_field_name(slug) != "slug":
                slug = f"{self.slug_prefix}-{slug}"
        return slug
