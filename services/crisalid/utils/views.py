from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import IsOwner, ReadOnly
from apps.commons.utils import map_action_to_permission
from apps.commons.views import OrganizationRelatedViewset
from apps.organizations.permissions import HasOrganizationPermission
from services.crisalid.models import Researcher


class ResearcherRelatedViewset(OrganizationRelatedViewset):
    """
    A viewset for models related to a researcher.

    This viewset should only be accessed through a URL containing the `researcher_id` and
    `organization_code` kwargs.
    e.g. `/v1/organizations/{organization_code}/researcher/{researcher_id}/my_model/`

    The viewset automatically handles filtering using the request user's permissions,
    and it provides the researcher in the serializer context.

    Attributes :
    ------------
    organization_code_url_kwarg: str (default: "organization_code")
        The name of the URL kwarg containing the organization code.
    researcher_id_url_kwarg: str (default: "researcher_id")
        The name of the URL kwarg containing the researcher id.
    queryset_organization_field: str (default: "researcher__organizations")
        The name of the field to use for filtering the queryset by organization.
    queryset_researcher_field: str (default: "researcher")
        The name of the field to use for filtering the queryset by researcher.
    read_only_permissions: bool (default: True)
        Whether the viewset should use read-only permissions. This is useful when the
        read permissions are handled at the instance level.
    permissions_app_label: str (default: "")
        The app label to use in the default permissions check
    permissions_base_codename: str (default: "")
        The base codename to use for generating the permissions to check. If not set,
        the `permissions_codename` attribute will be used as the codename for all actions.
    permissions_codename: str (default: "change_researcher")
        The codename to use for the default permissions check if`permissions_base_codename`
        is not set. This can be used if the same permission is used for all actions.
    multiple_lookup_fields: list of tuple[HasMultipleIDs, str] (default: [])
        Inherited from MultipleIDViewsetMixin. A list of tuples containing a model that
        inherits from HasMultipleIDs and the name of the URL kwarg containing the id to
        transform into the main id.
    """

    researcher_id_url_kwarg: str = "researcher_id"
    queryset_organization_field: str = "researcher__user__groups__organizations"
    queryset_researcher_field: str = "researcher"

    read_only_permissions: bool = True
    permissions_app_label: str = "crisalid"
    permissions_base_codename: str = ""
    permissions_codename: str = "change_researcher"

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
                    IsOwner
                    | ReadOnly
                    | HasBasePermission(codename, self.permissions_app_label)
                    | HasOrganizationPermission(codename),
                ]
            else:
                permissions = [
                    IsAuthenticated,
                    IsOwner
                    | HasBasePermission(codename, self.permissions_app_label)
                    | HasOrganizationPermission(codename),
                ]
            return permissions
        return super().get_permissions()

    def researcher_filter_queryset(self, queryset: "QuerySet") -> "QuerySet":
        """
        Filter the given queryset by the researcher specified in the URL.
        """
        return self.request.user.get_user_related_queryset(
            queryset.filter(**{self.queryset_researcher_field: self.researcher}),
            f"{self.queryset_researcher_field}__user",
        )

    def get_queryset(self):
        """
        Return the queryset for this viewset, filtered by the researcher and the
        organization specified in the URL.
        """
        return self.researcher_filter_queryset(super().get_queryset())

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "researcher": self.researcher,
        }

    @property
    def researcher(self) -> Researcher:
        if not hasattr(self, "_researcher"):
            if self.researcher_id_url_kwarg not in self.kwargs:
                raise ValueError(
                    f"URL kwarg '{self.researcher_id_url_kwarg}' is required for a"
                    f" viewset based on ResearcherRelatedViewset."
                )
            self._researcher = get_object_or_404(
                Researcher, id=self.kwargs[self.researcher_id_url_kwarg]
            )
        return self._researcher
