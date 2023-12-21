from typing import List, Tuple

from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets

from apps.commons.db.abc import HasMultipleIDs


class CreateListDestroyViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `retrieve`, `create`, and `list` actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class ListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    A viewset that provides `list` action.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class MultipleIDViewsetMixin:
    multiple_lookup_fields: List[Tuple[HasMultipleIDs, str]] = []

    def dispatch(self, request, *args, **kwargs):
        """
        Transform the id used for the request into the main id used by the viewset.
        """
        for model, field in self.multiple_lookup_fields:
            lookup_value = kwargs.get(field, None)
            if lookup_value is not None:
                method = getattr(self, f"get_{field}_from_lookup_value", None)
                if method is not None:
                    kwargs[field] = method(lookup_value)
                else:
                    kwargs[field] = model.get_main_id(lookup_value)
        return super().dispatch(request, *args, **kwargs)


class DetailOnlyViewsetMixin:
    def get_object(self):
        """
        Retrieve the object within the QuerySet.
        There should be only one object in the QuerySet.
        """
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj
