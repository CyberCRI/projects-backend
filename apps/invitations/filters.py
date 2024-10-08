from django_filters import rest_framework as filters

from .models import AccessRequest


class AccessRequestFilter(filters.FilterSet):
    class Meta:
        model = AccessRequest
        fields = ["status"]
