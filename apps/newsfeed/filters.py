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
        return queryset.filter(Q(end_date__gte=value))

    def range_filter_to(self, queryset, name, value):
        return queryset.filter(Q(end_date__lte=value))


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
