from django_filters import rest_framework as filters

from .models import Review


class ReviewFilter(filters.FilterSet):
    project = filters.CharFilter(field_name="project__id")
    reviewer = filters.CharFilter(field_name="reviewer__keycloak_id")

    class Meta:
        model = Review
        fields = ["project", "reviewer"]
