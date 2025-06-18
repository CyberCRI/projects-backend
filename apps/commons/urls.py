from rest_framework.routers import DefaultRouter, DynamicRoute, Route
from rest_framework.views import View


class ExtendedRouter(DefaultRouter):
    """
    Extendable router class that allows adding routes from other routers.
    """

    def extend(self, *routers: DefaultRouter):
        """
        Extend the routes with url routes of the passed in router.

        Args:
             router: DefaultRouter instance containing route definitions.
        """
        for router in routers:
            self.registry.extend(router.registry)


class OneToOneRouter(DefaultRouter):
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


class OneToOneExtendedRouter(OneToOneRouter, ExtendedRouter):
    """
    Extendable ListOnly router class that allows adding routes from other routers.
    """


def organization_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    prefix = r"organization/(?P<organization_code>[^/]+)"
    if path:
        prefix += r"/" + path
    router.register(prefix, viewset, basename)


def organization_project_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    prefix = r"organization/(?P<organization_code>[^/]+)/project/(?P<project_id>[^/]+)"
    if path:
        prefix += r"/" + path
    router.register(prefix, viewset, basename)


def project_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    prefix = r"project/(?P<project_id>[^/]+)"
    if path:
        prefix += r"/" + path
    router.register(prefix, viewset, basename)


def people_group_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    prefix = (
        r"organization/(?P<organization_code>[^/]+)/"
        r"people-group/(?P<people_group_id>[^/]+)"
    )
    if path:
        prefix += r"/" + path
    router.register(prefix, viewset, basename)


def organization_user_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    prefix = r"organization/(?P<organization_code>[^/]+)/user/(?P<user_id>[^/]+)"
    if path:
        prefix += r"/" + path
    router.register(prefix, viewset, basename)


def user_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    prefix = r"user/(?P<user_id>[^/]+)"
    if path:
        prefix += r"/" + path
    router.register(prefix, viewset, basename)
