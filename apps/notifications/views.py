import logging
from urllib.request import Request

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import IsOwner, ReadOnly
from apps.commons.views import (
    ListViewSet,
    NestedOrganizationUserViewMixins,
)
from apps.emailing.tasks import send_email_task
from apps.emailing.utils import render_message
from apps.notifications.filters import NotificationFilter
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission

from .serializers import (
    ContactSerializer,
    EmailReportSerializer,
    NotificationSettingsSerializer,
    NotificationsSerializer,
)

logger = logging.getLogger(__name__)


class NotificationsViewSet(NestedOrganizationUserViewMixins, ListViewSet):
    """Allows getting or modifying a user's notification."""

    permission_classes = [ReadOnly]
    serializer_class = NotificationsSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ("is_viewed", "created", "type")
    ordering = ("-created",)
    filterset_class = NotificationFilter

    def get_queryset(self):
        return (
            self.user.modules_by_organization(self.organization)
            .notifications()
            .select_related("sender", "project", "organization")
        )

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # update notifications
        self.get_queryset().filter(is_viewed=False).update(is_viewed=True)
        return response


class NotificationSettingsViewSet(NestedOrganizationUserViewMixins, viewsets.ViewSet):
    """Allows getting or modifying a user's notification settings."""

    serializer_class = NotificationSettingsSerializer
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]

    def list(self, request, *args, **kwargs):
        instance = self.user.notification_settings

        serializer = self.serializer_class(instance)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        instance = self.user.notification_settings

        serializer = self.serializer_class(
            instance,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class ReportViewSet(viewsets.GenericViewSet):
    """Viewset allowing to send email for bug or abuse report."""

    permission_classes = [AllowAny]
    serializer_class = EmailReportSerializer

    @extend_schema(request=EmailReportSerializer)
    @action(detail=False, methods=["POST"])
    def abuse(self, request: Request, *args, **kwargs):
        """Allow to send an abuse report email."""
        organization_code = self.kwargs.get("organization_code")
        organization = get_object_or_404(Organization, code=organization_code)
        serializer = EmailReportSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        text_content, html_content = render_message(
            "abuse",
            organization_url=organization.website_url,
            **serializer.validated_data,
        )
        send_email_task.delay(
            f"[Abuse] {serializer.validated_data['title']}",
            text_content,
            html_content=html_content,
            from_email=settings.EMAIL_REPORT_SENDER,
            to=[
                *settings.EMAIL_REPORT_RECIPIENTS,
                serializer.validated_data["reported_by"],
            ],
        )

        return Response(status=status.HTTP_200_OK)

    @extend_schema(request=EmailReportSerializer)
    @action(detail=False, methods=["POST"])
    def bug(self, request: Request, *args, **kwargs):
        """Allow to send a bug report email."""
        organization_code = self.kwargs.get("organization_code")
        organization = get_object_or_404(Organization, code=organization_code)
        serializer = EmailReportSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        text_content, html_content = render_message(
            "bug",
            organization_url=organization.website_url,
            **serializer.validated_data,
        )
        send_email_task.delay(
            f"[Bug] {serializer.validated_data['title']}",
            text_content,
            html_content=html_content,
            from_email=settings.EMAIL_REPORT_SENDER,
            to=[
                *settings.EMAIL_REPORT_RECIPIENTS,
                serializer.validated_data["reported_by"],
            ],
        )

        return Response(status=status.HTTP_200_OK)


class ContactViewSet(viewsets.GenericViewSet):
    """Viewset allowing to contact us."""

    permission_classes = [AllowAny]
    serializer_class = ContactSerializer

    @extend_schema(request=ContactSerializer)
    @action(detail=False, methods=["POST"])
    def us(self, request: Request, *args, **kwargs):
        """Allow to send an abuse report email."""
        organization_code = self.kwargs.get("organization_code")
        organization = get_object_or_404(Organization, code=organization_code)
        serializer = ContactSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        text_content, html_content = render_message(
            "contact_us",
            organization_url=organization.website_url,
            **serializer.validated_data,
        )
        send_email_task.delay(
            f"[Contact] {serializer.validated_data['subject']}",
            text_content,
            html_content=html_content,
            from_email=settings.EMAIL_CONTACT_SENDER,
            to=[
                *settings.EMAIL_CONTACT_RECIPIENTS,
                serializer.validated_data["email"],
            ],
        )

        return Response(status=status.HTTP_200_OK)
