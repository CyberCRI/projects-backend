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
