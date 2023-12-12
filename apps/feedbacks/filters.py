from django_filters import rest_framework as filters

from apps.commons.filters import UserMultipleIDFilter

from .models import Review


class ReviewFilter(filters.FilterSet):
    project = filters.CharFilter(field_name="project__id")
    reviewer = UserMultipleIDFilter(field_name="reviewer__id")

    class Meta:
        model = Review
        fields = ["project", "reviewer"]
