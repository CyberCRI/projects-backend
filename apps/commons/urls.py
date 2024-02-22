from rest_framework.routers import DefaultRouter
from rest_framework.views import View


class ExtendedRouter(DefaultRouter):
    """
    Extends `DefaultRouter` class to add a method for extending url routes from another router.
    """

    def extend(self, router):
        """
        Extend the routes with url routes of the passed in router.

        Args:
             router: SimpleRouter instance containing route definitions.
        """
        self.registry.extend(router.registry)


def organization_router_register(
    router: DefaultRouter, prefix: str, viewset: View, basename: str = None
):
    router.register(
        r"organization/(?P<organization_code>[^/]+)/" + prefix, viewset, basename
    )


def project_router_register(
    router: DefaultRouter, prefix: str, viewset: View, basename: str = None
):
    router.register(
        r"organization/(?P<organization_code>[^/]+)/"
        r"project/(?P<project_id>[^/]+)/" + prefix,
        viewset,
        basename,
    )
