from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission, ReadOnly
from apps.commons.permissions import IsOwner
from apps.commons.utils.permissions import map_action_to_permission
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from apps.organizations.utils import get_hierarchy_codes

from .models import Invitation
from .serializers import InvitationSerializer


class InvitationViewSet(viewsets.ModelViewSet):
    queryset = Invitation.objects.all()
    serializer_class = InvitationSerializer
    filter_backends = (
        DjangoFilterBackend,
        OrderingFilter,
    )

    ordering_fields = [
        "expire_at",
        "owner__given_name",
        "owner__family_name",
        "people_group__name",
    ]

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "invitation")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | IsOwner
                | HasBasePermission(codename, "invitations")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self):
        codes = [self.kwargs.get("organization_code")]
        return self.queryset.filter(organization__code__in=get_hierarchy_codes(codes))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["organization_code"] = self.kwargs.get("organization_code")
        return context

    def perform_create(self, serializer):
        code = self.kwargs.get("organization_code")
        organization = Organization.objects.get(code=code)
        serializer.save(organization=organization, owner=self.request.user)
