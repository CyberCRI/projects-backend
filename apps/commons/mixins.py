from collections.abc import Iterable
from contextlib import suppress
from copy import copy
from typing import TYPE_CHECKING, Any, Optional, Self

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from guardian.models import GroupObjectPermission
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

    def get_related_organizations(self) -> list["Organization"]:
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

    def get_related_organizations(self) -> list["Organization"]:
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
        try:
            group.data
        except GroupData.DoesNotExist:
            GroupData.objects.update_or_create(
                group=group,
                defaults={
                    "role": name,
                    "content_type": self.content_type,
                    "object_id": self.pk,
                },
            )
        return group

    def setup_permissions(self, user: Optional["ProjectUser"] = None):
        """Initialize permissions for the instance."""
        raise NotImplementedError()

    @classmethod
    def batch_reassign_permissions(
        cls, roles_permissions: tuple[str, Iterable[Permission]]
    ):
        """
        Reassign permissions for all instances of the model.

        This is useful for bulk updating permissions after changing the permissions
        assigned to default roles.

        Arguments:
        ----------
            roles_permissions: A tuple containing the role names its permissions
            eg : roles_permissions=(
                ("admins", QuerySet([<Permission: change_obj>, <Permission: delete_obj>])),
                ("viewers", QuerySet([<Permission: view_obj>])),
            )
        """

        cls.objects.update(permissions_up_to_date=False)
        content_type = ContentType.objects.get_for_model(cls)
        roles = [role for role, _ in roles_permissions]

        # Make sure all groups exist
        groups_to_create = [
            Group(name=f"{content_type.model}:#{instance.pk}:{role}")
            for instance in cls.objects.all()
            for role in roles
        ]
        Group.objects.bulk_create(
            groups_to_create,
            batch_size=1000,
            ignore_conflicts=True,
        )

        # Make sure all GroupData exist
        group_data_to_create = [
            GroupData(
                group=group,
                role=group.name.split(":")[-1],
                content_type=content_type,
                object_id=group.name.split(":")[-2][1:],
            )
            for group in Group.objects.filter(
                name__startswith=f"{content_type.model}:#"
            )
        ]
        GroupData.objects.bulk_create(
            group_data_to_create,
            batch_size=1000,
            update_conflicts=True,
            update_fields=["role", "content_type", "object_id"],
            unique_fields=["group"],
        )

        # Reassign permissions
        permissions_to_create = []
        for role, permissions in roles_permissions:
            groups_datas = GroupData.objects.filter(
                role=role, content_type=content_type
            )
            permissions_to_create = [
                GroupObjectPermission(
                    group_id=data.group_id,
                    permission=perm,
                    object_pk=data.object_id,
                    content_type=content_type,
                )
                for data in groups_datas
                for perm in permissions
            ]
            GroupObjectPermission.objects.filter(
                content_type=content_type,
                group__data__role=role,
            ).exclude(permission__in=permissions).delete()
            GroupObjectPermission.objects.bulk_create(
                permissions_to_create, ignore_conflicts=True, batch_size=1000
            )
        cls.objects.update(permissions_up_to_date=True)


class DuplicableModel:
    """
    A model that can be duplicated.
    """

    def duplicate(self, **fields) -> type[Self]:
        """duplicate models elements, set new fields

        :return: new models
        """

        instance_copy = copy(self)
        instance_copy.pk = None

        for name, value in fields.items():
            setattr(instance_copy, name, value)

        # remove prefetch m2m
        with suppress(AttributeError):
            del instance_copy._prefetched_objects_cache

        instance_copy.save()
        return instance_copy


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

    _original_slug_fields_value: dict[str, str] = {}
    slugified_fields: list[str] = []
    reserved_slugs: list[str] = []
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
        cls, objects_ids: list[Any], returned_field: str = "id"
    ) -> list[Any]:
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


class HasModulesRelated:
    """Mixins for related modules class"""

    def get_related_module(self):
        from apps.modules.base import get_module

        return get_module(type(self))


class HasEmbending:
    def vectorize(self):
        if not getattr(self, "embedding", None):
            model_embedding = type(self).embedding.related.related_model
            self.embedding = model_embedding(item=self)
            self.embedding.save()
        self.embedding.vectorize()

    def similars(self, threshold: float = 0.15) -> QuerySet[Self]:
        """return similars documents"""
        if getattr(self, "embedding", None):
            vector = self.embedding.embedding
            model_embedding = type(self).embedding.related.related_model
            queryset = type(self).objects.all()
            return model_embedding.vector_search(vector, queryset, threshold).exclude(
                pk=self.pk
            )
        return type(self).objects.all()
