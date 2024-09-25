from rest_framework import viewsets

from apps.commons.permissions import ReadOnly

from .filters import EscoTagFilter
from .models import EscoTag
from .serializers import EscoTagSerializer


class EscoTagViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ReadOnly]
    queryset = EscoTag.objects.all()
    filterset_class = EscoTagFilter
    serializer_class = EscoTagSerializer
