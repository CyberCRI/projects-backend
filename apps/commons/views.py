from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.settings import api_settings

from apps.accounts.models import ProjectUser
from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import IsOwner, ReadOnly, WillBeOwner
from apps.commons.utils import map_action_to_permission
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.permissions import HasProjectPermission, ProjectIsNotLocked

from .mixins import HasMultipleIDs


class CreateListDestroyViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `retrieve`, `create`, and `list` actions.

    To use it, override the class and set the `queryset` and
    `serializer_class` attributes.
    """


class ListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    A viewset that provides `list` action.

    To use it, override the class and set the `queryset` and
    `serializer_class` attributes.
    """


class WriteOnlyModelViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `create` and `update` actions.

    To use it, override the class and set the `queryset` and
    `serializer_class` attributes.
    """


class ReadDestroyModelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `retrieve`, `list`, `update`, and `destroy` actions.

    To use it, override the class and set the `queryset` and
    `serializer_class` attributes.
    """


class MultipleIDViewsetMixin:
    multiple_lookup_fields: list[tuple[HasMultipleIDs, str]] = []

    def dispatch(self, request, *args, **kwargs):
        """
        Transform the id used for the request into the main id used by the viewset.
        """
        for model, field in self.multiple_lookup_fields:
            lookup_value = kwargs.get(field)
            if lookup_value is not None:
                method = getattr(self, f"get_{field}_from_lookup_value", None)
                if method is not None:
                    kwargs[field] = method(lookup_value)
                else:
                    kwargs[field] = model.get_main_id(lookup_value)
        return super().dispatch(request, *args, **kwargs)


class DetailOnlyViewsetMixin:
    def get_object(self):
        """
        Retrieve the object within the QuerySet.
        There should be only one object in the QuerySet.
        """
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj


class PaginatedViewSet(viewsets.ViewSet):
    """
    A viewset that allows paginated responses for viewsets not based on models.
    """

    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    serializer_class = None

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_paginated_list(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(
                page, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(
            queryset, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)


class OrganizationRelatedViewset(viewsets.GenericViewSet):
    organization_code_url_kwarg: str = "organization_code"
    queryset_organization_field: str = "organization"

    read_only_permissions: bool = True
    permissions_app_label: str = ""
    permissions_base_codename: str = ""

    def get_permissions(self):
        if self.permissions_base_codename and self.permissions_app_label:
            codename = map_action_to_permission(
                self.action, self.permissions_base_codename
            )
            if self.read_only_permissions:
                return [
                    IsAuthenticatedOrReadOnly,
                    ReadOnly
                    | HasBasePermission(codename, self.permissions_app_label)
                    | HasOrganizationPermission(codename),
                ]
            return [
                IsAuthenticated,
                HasBasePermission(codename, self.permissions_app_label)
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def organization_filter_queryset(self, queryset: "QuerySet") -> "QuerySet":
        """
        Filter the given queryset by the organization specified in the URL.
        """
        return queryset.filter(**{self.queryset_organization_field: self.organization})

    def get_queryset(self):
        """
        Return the queryset for this viewset, filtered by the organization specified
        in the URL.
        """
        return self.organization_filter_queryset(super().get_queryset())

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "organization": self.organization,
        }

    @property
    def organization(self) -> Organization:
        if not hasattr(self, "_organization"):
            if self.organization_code_url_kwarg not in self.kwargs:
                raise ValueError(
                    f"URL kwarg '{self.organization_code_url_kwarg}' is required for a"
                    f" viewset based on OrganizationRelatedViewset."
                )
            self._organization = get_object_or_404(
                Organization, code=self.kwargs[self.organization_code_url_kwarg]
            )
        return self._organization


class ProjectRelatedViewset(MultipleIDViewsetMixin, OrganizationRelatedViewset):
    """
    A viewset for models relared to a project.

    This viewset should only be accessed through a URL containing the `project_id` and
    `organization_code` kwargs.
    e.g. `/v1/organizations/{organization_code}/projects/{project_id}/my_model/`

    The viewset automatically handles filtering using the request user's permissions,
    and it provides the project in the serializer context.

    Attributes :
    ------------
    organization_code_url_kwarg: str (default: "organization_code")
        The name of the URL kwarg containing the organization code.
    project_id_url_kwarg: str (default: "project_id")
        The name of the URL kwarg containing the project id.
    queryset_organization_field: str (default: "project__organizations")
        The name of the field to use for filtering the queryset by organization.
    queryset_project_field: str (default: "project")
        The name of the field to use for filtering the queryset by project.
    read_only_permissions: bool (default: True)
        Whether the viewset should use read-only permissions. This is useful when the
        read permissions are handled at the instance level.
    block_if_project_is_locked: bool (default: True)
        Whether to block all actions if the project is locked.
    permissions_app_label: str (default: "")
        The app label to use in the default permissions check
    permissions_base_codename: str (default: "")
        The base codename to use for generating the permissions to check. If not set,
        the `permissions_codename` attribute will be used as the codename for all actions.
    permissions_codename: str (default: "change_project")
        The codename to use for the default permissions check if`permissions_base_codename`
        is not set. This can be used if the same permission is used for all actions.
    multiple_lookup_fields: list of tuple[HasMultipleIDs, str] (default: [])
        Inherited from MultipleIDViewsetMixin. A list of tuples containing a model that
        inherits from HasMultipleIDs and the name of the URL kwarg containing the id to
        transform into the main id.
    """

    project_id_url_kwarg: str = "project_id"
    queryset_organization_field: str = "project__organizations"
    queryset_project_field: str = "project"

    read_only_permissions: bool = True
    block_if_project_is_locked: bool = True
    permissions_app_label: str = "projects"
    permissions_base_codename: str = ""
    permissions_codename: str = "change_project"

    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_permissions(self):
        if self.permissions_base_codename:
            codename = map_action_to_permission(
                self.action, self.permissions_base_codename
            )
        else:
            codename = self.permissions_codename
        if codename and self.permissions_app_label:
            if self.read_only_permissions:
                permissions = [
                    IsAuthenticatedOrReadOnly,
                    ReadOnly
                    | HasBasePermission(codename, self.permissions_app_label)
                    | HasOrganizationPermission(codename)
                    | HasProjectPermission(codename),
                ]
            else:
                permissions = [
                    IsAuthenticated,
                    HasBasePermission(codename, self.permissions_app_label)
                    | HasOrganizationPermission(codename)
                    | HasProjectPermission(codename),
                ]
            if self.block_if_project_is_locked:
                permissions.insert(1, ProjectIsNotLocked)
            return permissions
        return super().get_permissions()

    def project_filter_queryset(self, queryset: "QuerySet") -> "QuerySet":
        """
        Filter the given queryset by the project specified in the URL.
        """
        return self.request.user.get_project_related_queryset(
            queryset.filter(**{self.queryset_project_field: self.project}),
            self.queryset_project_field,
        )

    def get_queryset(self):
        """
        Return the queryset for this viewset, filtered by the project and the
        organization specified in the URL.
        """
        return self.project_filter_queryset(super().get_queryset())

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "project": self.project,
        }

    @property
    def project(self) -> Project:
        if not hasattr(self, "_project"):
            if self.project_id_url_kwarg not in self.kwargs:
                raise ValueError(
                    f"URL kwarg '{self.project_id_url_kwarg}' is required for a"
                    f" viewset based on ProjectRelatedViewset."
                )
            self._project = get_object_or_404(
                Project, id=self.kwargs[self.project_id_url_kwarg]
            )
        return self._project


class UserRelatedViewset(OrganizationRelatedViewset):
    user_id_url_kwarg: str = "user_id"
    queryset_organization_field: str = "user__groups__organizations"
    queryset_user_field: str = "user"

    read_only_permissions: bool = True
    permissions_app_label: str = "accounts"
    permissions_base_codename: str = ""
    permissions_codename: str = "change_projectuser"

    def get_permissions(self):
        if self.permissions_base_codename:
            codename = map_action_to_permission(
                self.action, self.permissions_base_codename
            )
        else:
            codename = self.permissions_codename
        if codename and self.permissions_app_label:
            if self.read_only_permissions:
                return [
                    IsAuthenticatedOrReadOnly,
                    ReadOnly
                    | IsOwner
                    | WillBeOwner
                    | HasBasePermission(codename, self.permissions_app_label)
                    | HasOrganizationPermission(codename),
                ]
            return [
                IsAuthenticated,
                IsOwner
                | WillBeOwner
                | HasBasePermission(codename, self.permissions_app_label)
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def user_filter_queryset(self, queryset: "QuerySet") -> "QuerySet":
        """
        Filter the given queryset by the user specified in the URL and by the read
        permimssions given to the request user.
        """
        return self.request.user.get_user_related_queryset(
            queryset.filter(**{self.queryset_user_field: self.user}),
            self.queryset_user_field,
        )

    def get_queryset(self):
        """
        Return the queryset for this viewset, filtered by the user specified in the URL
        and by the read permimssions given to the request user.
        """
        return self.user_filter_queryset(super().get_queryset())

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "user": self.user,
        }

    @property
    def user(self) -> ProjectUser:
        if not hasattr(self, "_user"):
            if self.user_id_url_kwarg not in self.kwargs:
                raise ValueError(
                    f"URL kwarg '{self.user_id_url_kwarg}' is required for a"
                    f" viewset based on UserRelatedViewset."
                )
            self._user = get_object_or_404(
                ProjectUser, id=self.kwargs[self.user_id_url_kwarg]
            )
        return self._user
