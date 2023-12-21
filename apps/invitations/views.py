import uuid

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission, ReadOnly
from apps.commons.permissions import IsOwner
from apps.commons.utils.permissions import map_action_to_permission
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission

from .models import Invitation
from .serializers import InvitationSerializer


class InvitationViewSet(viewsets.ModelViewSet):
    serializer_class = InvitationSerializer
    lookup_field = "id"
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

    def get_object(self):
        try:
            uuid_obj = uuid.UUID(self.kwargs["id"], version=4)
            obj = Invitation.objects.filter(token=uuid_obj).first()
            if obj:
                self.kwargs["id"] = obj.id
        except ValueError:
            pass
        return super().get_object()

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
        if "organization_code" in self.kwargs:
            return Invitation.objects.filter(
                organization__code=self.kwargs["organization_code"]
            )
        return Invitation.objects.none()

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "organization_code": self.kwargs.get("organization_code"),
        }

    def perform_create(self, serializer):
        code = self.kwargs.get("organization_code")
        organization = Organization.objects.get(code=code)
        serializer.save(organization=organization, owner=self.request.user)
