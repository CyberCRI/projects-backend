from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Event, Instruction, News


class EventFilter(filters.FilterSet):
    from_date = filters.CharFilter(method="range_filter_from", label="form_date")
    to_date = filters.CharFilter(method="range_filter_to", label="to_date")

    class Meta:
        model = Event
        fields = ["from_date", "to_date"]

    def range_filter_from(self, queryset, name, value):
        # filter by end_date (to catch event current running (start_date before value but end_date after))
        return queryset.filter(end_date__gte=value)

    def range_filter_to(self, queryset, name, value):
        # same above but with start_date
        return queryset.filter(start_date__lte=value)


class InstructionFilter(filters.FilterSet):
    from_date = filters.DateTimeFilter(field_name="publication_date", lookup_expr="gte")
    to_date = filters.DateTimeFilter(field_name="publication_date", lookup_expr="lte")

    class Meta:
        model = Instruction
        fields = ["from_date", "to_date"]


class NewsFilter(filters.FilterSet):
    from_date = filters.DateTimeFilter(field_name="publication_date", lookup_expr="gte")
    to_date = filters.DateTimeFilter(field_name="publication_date", lookup_expr="lte")

    class Meta:
        model = News
        fields = ["from_date", "to_date"]
