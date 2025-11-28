import os

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


ORGANIZATION_PREFIX = r"organization/(?P<organization_code>[^/]+)"
PEOPLEGROUP_PREFIX = r"people-group/(?P<people_group_id>[^/]+)"
RESEARCHER_PREFIX = r"researcher/(?P<researcher_id>[^/]+)"
PROJECT_PREFIX = r"project/(?P<project_id>[^/]+)"
USER_PREFIX = r"user/(?P<user_id>[^/]+)"


def organization_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    url = os.path.join(ORGANIZATION_PREFIX, path)
    router.register(url, viewset, basename)


def organization_project_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    url = os.path.join(ORGANIZATION_PREFIX, PROJECT_PREFIX, path)
    router.register(url, viewset, basename)


def project_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    url = os.path.join(PROJECT_PREFIX, path)
    router.register(url, viewset, basename)


def organization_people_group_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    url = os.path.join(ORGANIZATION_PREFIX, PEOPLEGROUP_PREFIX, path)
    router.register(url, viewset, basename)


def organization_user_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    url = os.path.join(ORGANIZATION_PREFIX, USER_PREFIX, path)
    router.register(url, viewset, basename)


def user_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    url = os.path.join(USER_PREFIX, path)
    router.register(url, viewset, basename)


def organization_researcher_router_register(
    router: DefaultRouter, path: str, viewset: View, basename: str = None
):
    url = os.path.join(ORGANIZATION_PREFIX, RESEARCHER_PREFIX, path)
    router.register(url, viewset, basename)
