import uuid

from django.db.models import QuerySet
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import ReadOnly
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.news.models import News
from apps.news.serializer import NewsSerializer
from apps.organizations.permissions import HasOrganizationPermission


class NewsViewSet(viewsets.ModelViewSet):
    """Main endpoints for projects."""

    serializer_class = NewsSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "updated_at"]
    lookup_field = "id"
    lookup_value_regex = "[^/]+"
    multiple_lookup_fields = [
        (News, "id"),
    ]
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_news", "news")
        | HasOrganizationPermission("change_news"),
    ]

    def get_queryset(self) -> QuerySet:

        return self.request.user.get_news_queryset()


class NewsHeaderView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_news", "news")
        | HasOrganizationPermission("change_news"),
    ]

    def get_queryset(self):
        if "news_id" in self.kwargs:
            return Image.objects.filter(news_header__id=self.kwargs["news_id"])
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"news/header/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image):
        if "news_id" in self.kwargs:
            news = News.objects.get(id=self.kwargs["news_id"])
            news.header_image = image
            news.save()
            return f"/v1/organization/{self.kwargs['organization_code']}/news/{self.kwargs['news_id']}/header/{image.id}"
        return None
