from typing import List, Tuple

from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.settings import api_settings

from .models import HasMultipleIDs


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


class PaginatedViewSet(viewsets.ViewSet):
    """
    A viewset that allows paginated responses for viewsets not based on models.
    """

    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    serializer_class = None

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {"request": self.request, "format": self.format_kwarg, "view": self}

    def get_paginated_list(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(
                page, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(
            queryset, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)
