from typing import List

from rest_framework import mixins, viewsets


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
    multiple_lookup_fields: List[str] = []

    def dispatch(self, request, *args, **kwargs):
        """
        Transform the id used for the request into the main id used by the viewset.
        """
        for field in self.multiple_lookup_fields:
            lookup_value = kwargs.get(field, None)
            if lookup_value is not None:
                method = getattr(self, f"get_{field}_from_lookup_value", None)
                if method is not None:
                    kwargs[field] = method(lookup_value)
                else:
                    raise NotImplementedError(
                        f"get_{field}_from_lookup_value method is not implemented"
                    )
        return super().dispatch(request, *args, **kwargs)
