import json
import uuid

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import (
    CreateOnly,
    IsAuthenticatedOrCreateOnly,
    IsOwner,
    ReadOnly,
)
from apps.commons.serializers.serializers import CreateListModelViewSet
from apps.commons.utils.permissions import map_action_to_permission
from apps.invitations.models import AccessRequest
from apps.invitations.serializers import (
    AccessRequestManySerializer,
    AccessRequestSerializer,
    ProcessAccessRequestSerializer,
)
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from keycloak import KeycloakGetError, KeycloakPostError, KeycloakPutError

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


class AccessRequestViewSet(CreateListModelViewSet):
    serializer_class = AccessRequestSerializer
    permission_classes = [
        IsAuthenticatedOrCreateOnly,
        CreateOnly
        | HasBasePermission("manage_accessrequest", "invitations")
        | HasOrganizationPermission("manage_accessrequest"),
    ]

    def get_queryset(self):
        if "organization_code" in self.kwargs:
            return AccessRequest.objects.filter(
                organization__code=self.kwargs["organization_code"]
            )
        return AccessRequest.objects.none()

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "organization_code": self.kwargs.get("organization_code", None),
        }

    def create(self, request, *args, **kwargs):
        request.data.update(
            {
                "organization": self.kwargs["organization_code"],
                "user": request.user.id if request.user.is_authenticated else None,
            }
        )
        return super().create(request, *args, **kwargs)

    def perform_accept(self, access_request: AccessRequest):
        if access_request.organization.code != self.kwargs["organization_code"]:
            return {
                "status": "error",
                "message": "This access request is not for the current organization.",
            }
        if access_request.status != AccessRequest.Status.PENDING:
            return {
                "status": "error",
                "message": "This access request has already been processed.",
            }
        try:
            if access_request.user is not None:
                access_request.accept()
            else:
                access_request.accept_and_create()
        except KeycloakGetError:
            return {
                "status": "warning",
                "message": "Confirmation email not sent to user",
            }
        except (KeycloakPostError, KeycloakPutError) as e:
            message = json.loads(e.response_body.decode()).get("errorMessage")
            return {"status": "error", "message": f"Keycloak error : {message}"}
        except Exception as e:  # noqa
            return {"status": "error", "message": str(e)}
        return {"status": "success", "message": ""}

    def perform_decline(self, access_request: AccessRequest):
        if access_request.organization.code != self.kwargs["organization_code"]:
            return {
                "status": "error",
                "message": "This access request is not for the current organization.",
            }
        if access_request.status != AccessRequest.Status.PENDING:
            return {
                "status": "error",
                "message": "This access request has already been processed.",
            }
        try:
            access_request.decline()
        except Exception as e:  # noqa
            return {"status": "error", "message": str(e)}
        return {"status": "success", "message": ""}

    @extend_schema(
        request=AccessRequestManySerializer, responses=ProcessAccessRequestSerializer
    )
    @action(detail=False, methods=["POST"])
    def accept(self, request, *args, **kwargs):
        serializer = AccessRequestManySerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        results = {
            "success": [],
            "error": [],
            "warning": [],
        }
        for access_request in serializer.validated_data["access_requests"]:
            result = self.perform_accept(access_request)
            results[result["status"]].append(
                {
                    "id": access_request.id,
                    "email": (
                        access_request.email
                        if not access_request.user
                        else access_request.user.email
                    ),
                    "message": result["message"],
                }
            )
        serializer = ProcessAccessRequestSerializer(data=results)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AccessRequestManySerializer, responses=ProcessAccessRequestSerializer
    )
    @action(detail=False, methods=["POST"])
    def decline(self, request, *args, **kwargs):
        serializer = AccessRequestManySerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        results = {
            "success": [],
            "error": [],
            "warning": [],
        }
        for access_request in serializer.validated_data["access_requests"]:
            result = self.perform_decline(access_request)
            results[result["status"]].append(
                {
                    "id": access_request.id,
                    "email": (
                        access_request.email
                        if not access_request.user
                        else access_request.user.email
                    ),
                    "message": result["message"],
                }
            )
        serializer = ProcessAccessRequestSerializer(data=results)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
