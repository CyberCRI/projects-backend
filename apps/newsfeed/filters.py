from django_filters import rest_framework as filters

from .models import Event, Instruction, News


class EventFilter(filters.FilterSet):
    from_date = filters.DateTimeFilter(field_name="event_date", lookup_expr="gte")
    to_date = filters.DateTimeFilter(field_name="event_date", lookup_expr="lte")

    class Meta:
        model = Event
        fields = ["from_date", "to_date"]


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
