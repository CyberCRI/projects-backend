import logging
from urllib.request import Request

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.models import ProjectUser
from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import IsOwner, ReadOnly
from apps.commons.serializers import RetrieveUpdateModelViewSet
from apps.commons.views import ListViewSet, MultipleIDViewsetMixin
from apps.emailing.tasks import send_email_task
from apps.emailing.utils import render_message
from apps.organizations.permissions import HasOrganizationPermission

from .models import Notification, NotificationSettings
from .serializers import (
    ContactSerializer,
    EmailReportSerializer,
    NotificationSettingsSerializer,
    NotificationsSerializer,
)

logger = logging.getLogger(__name__)


class NotificationsViewSet(ListViewSet):
    """Allows getting or modifying a user's notification."""

    permission_classes = [ReadOnly]
    serializer_class = NotificationsSerializer

    def get_queryset(self):
        return (
            Notification.objects.filter(receiver=self.request.user)
            .order_by("-created")
            .select_related("sender", "project", "organization")
        )

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        response = super(NotificationsViewSet, self).list(request, *args, **kwargs)
        Notification.objects.filter(receiver=self.request.user).update(is_viewed=True)
        return response


class NotificationSettingsViewSet(MultipleIDViewsetMixin, RetrieveUpdateModelViewSet):
    """Allows getting or modifying a user's notification settings."""

    serializer_class = NotificationSettingsSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]
    multiple_lookup_fields = [
        (ProjectUser, "user_id"),
    ]

    def get_queryset(self):
        if "user_id" in self.kwargs:
            qs = self.request.user.get_user_related_queryset(
                NotificationSettings.objects.all()
            )
            return qs.filter(user__id=self.kwargs["user_id"])
        return NotificationSettings.objects.none()


class ReportViewSet(viewsets.GenericViewSet):
    """Viewset allowing to send email for bug or abuse report."""

    permission_classes = [AllowAny]
    serializer_class = EmailReportSerializer

    @extend_schema(request=EmailReportSerializer)
    @action(detail=False, methods=["POST"])
    def abuse(self, request: Request):
        """Allow to send an abuse report email."""
        serializer = EmailReportSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        text_content, html_content = render_message(
            "abuse", **serializer.validated_data
        )
        send_email_task.delay(
            f"[Abuse] {serializer.validated_data['title']}",
            text_content,
            settings.EMAIL_REPORT_RECIPIENTS,
            html_content=html_content,
        )

        return Response(status=status.HTTP_200_OK)

    @extend_schema(request=EmailReportSerializer)
    @action(detail=False, methods=["POST"])
    def bug(self, request: Request):
        """Allow to send a bug report email."""
        serializer = EmailReportSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        text_content, html_content = render_message("bug", **serializer.validated_data)
        send_email_task.delay(
            f"[Bug] {serializer.validated_data['title']}",
            text_content,
            settings.EMAIL_REPORT_RECIPIENTS,
            html_content=html_content,
        )

        return Response(status=status.HTTP_200_OK)


class ContactViewSet(viewsets.GenericViewSet):
    """Viewset allowing to contact us."""

    permission_classes = [AllowAny]
    serializer_class = ContactSerializer

    @extend_schema(request=ContactSerializer)
    @action(detail=False, methods=["POST"])
    def us(self, request: Request):
        """Allow to send an abuse report email."""
        serializer = ContactSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        text_content, html_content = render_message(
            "contact_us", **serializer.validated_data
        )
        send_email_task.delay(
            f"[Contact] {serializer.validated_data['subject']}",
            text_content,
            settings.EMAIL_REPORT_RECIPIENTS,
            html_content=html_content,
        )

        return Response(status=status.HTTP_200_OK)
