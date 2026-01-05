from functools import wraps
from typing import Any

from apps.commons.admin import RouterExtraAdmin
from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.http.request import HttpRequest
from django.urls import path


class ExtraAdminSite(admin.AdminSite):
    """ExtrasAdminSite to add custom view in admins"""

    def __init__(self, *ar, **kw):
        super().__init__(*ar, **kw)

        self.__extras_router: dict[str, RouterExtraAdmin] = {}

    def register_extras(self, menu_name: str, path: str, view, **kw):
        if menu_name not in self.__extras_router:
            self.__extras_router[menu_name] = RouterExtraAdmin(menu_name)

        router = self.__extras_router[menu_name]
        router.register(path, view, **kw)

    def _extras(self) -> list[RouterExtraAdmin]:
        """Generate Extra views."""
        return self.__extras_router.values()

    @wraps(admin.AdminSite.get_urls)
    def get_urls(self):
        urls = super().get_urls()
        for app_extra in self._extras():
            app_label = app_extra.app_label
            for url, view, kw_models, kw in app_extra.views:
                admin_app = {"app_label": app_label, **kw, **kw_models}
                object_name = admin_app["object_name"]
                admin_app.setdefault("title", admin_app.get("name"))
                admin_app["app_list"] = [admin_app]
                urls.insert(
                    0,
                    path(
                        url,
                        self.admin_view(
                            view.as_view(admin_site=self, admin_app=admin_app)
                        ),
                        name=f"{app_label}-{object_name}",
                    ),
                )
        return urls

    def _handel_extras_permission(self, request: HttpRequest, app: dict) -> dict | None:
        """Check if extra custom view is permission Ok for this user."""

        user = request.user
        models = app["models"].copy()
        app["models"] = []

        for obj in models:
            permissions = obj.get("permissions") or {}
            if permissions.get("superuser") and not user.is_superuser:
                continue
            app["models"].append(obj)

        if app["models"]:
            return app
        return None

    def get_app_list(self, request: HttpRequest) -> list[Any]:
        app_list = []
        for app_extra in self._extras():
            if app := self._handel_extras_permission(request, app_extra.app):
                app_list.append(app)
        app_list.extend(super().get_app_list(request))
        return app_list


class ExtraAdminConfig(AdminConfig):
    default_site = "projects.admin.ExtraAdminSite"
