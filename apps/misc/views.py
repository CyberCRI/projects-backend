from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission
from apps.commons.filters import TrigramSearchFilter
from apps.commons.permissions import ReadOnly, map_action_to_permission
from apps.misc import filters, models, serializers
from apps.organizations.permissions import HasOrganizationPermission


class WikipediaTagViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.WikipediaTagSerializer
    filter_backends = (
        TrigramSearchFilter,
        DjangoFilterBackend,
        OrderingFilter,
    )
    filterset_class = filters.WikipediaTagFilter
    search_fields = ["name_fr", "name_en"]
    lookup_field = "wikipedia_qid"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "wikipediatag")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly | HasBasePermission(codename, "misc"),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        return models.WikipediaTag.objects.all()


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TagSerializer
    filter_backends = (
        TrigramSearchFilter,
        DjangoFilterBackend,
        OrderingFilter,
    )
    filterset_class = filters.TagFilter
    search_fields = ["name"]
    queryset = models.Tag.objects.all()

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "tag")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "misc")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()
