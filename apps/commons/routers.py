from rest_framework.routers import DefaultRouter, DynamicRoute, Route
from rest_framework_nested.routers import NestedMixin


class DetailOnlyNestedRouter(NestedMixin, DefaultRouter):
    """Remove the `list` action and move all action to the `-list` url.

    This is useful for one to one nested object, since giving the object's PK
    can be redundant if its parent's is enough.

    ViewSets using this router should probably override the `get_object`
    method to retrieve the object using the parent's PK.
    """

    routes = [
        # List route.
        Route(
            url=r"^{prefix}{trailing_slash}$",
            mapping={
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
                "post": "create",
            },
            name="{basename}-list",
            detail=False,
            initkwargs={"suffix": "List"},
        ),
        # Dynamically generated list routes. Generated using
        # @action(detail=False) decorator on methods of the viewset.
        DynamicRoute(
            url=r"^{prefix}/{url_path}{trailing_slash}$",
            name="{basename}-{url_name}",
            detail=False,
            initkwargs={},
        ),
    ]
