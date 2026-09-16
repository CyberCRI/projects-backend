from django_filters import FilterSet, filters

from apps.notifications.models import Notification


class NotificationFilter(FilterSet):
    type = filters.MultipleChoiceFilter(field_name="type", lookup_expr="in")
    is_viewed = filters.BooleanFilter(field_name="is_viewed")

    class Meta:
        model = Notification
        fields = ["type", "is_viewed"]
