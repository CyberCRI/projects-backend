from rest_framework import viewsets

from apps.commons.permissions import ReadOnly

from .filters import EscoOccupationFilter, EscoSkillFilter
from .models import EscoOccupation, EscoSkill
from .serializers import EscoOccupationSerializer, EscoSkillSerializer


class EscoSkillViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ReadOnly]
    queryset = EscoSkill.objects.all()
    filterset_class = EscoSkillFilter
    serializer_class = EscoSkillSerializer


class EscoOccupationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ReadOnly]
    queryset = EscoOccupation.objects.all()
    filterset_class = EscoOccupationFilter
    serializer_class = EscoOccupationSerializer
