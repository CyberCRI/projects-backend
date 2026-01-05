import os
from functools import wraps
from typing import Any

from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.http.request import HttpRequest
from django.urls import path
from django.views import View


class RouterExtraAdmin:
    """Router to add custom route to admin django (need to add ExtraAdminMixins to your views)"""

    def __init__(self, name: str, app_label: str | None = None):
        self.name = name
        self.app_label = app_label or name
        self._register: list[tuple[str, type[View], dict, dict]] = []

    def register(
        self,
        path: str,
        view: View,
        name=None,
        object_name=None,
        model=None,
        permissions=None,
        view_only=True,
        **kw,
    ):
        kw_models = {
            "name": name or path,
            "object_name": object_name or path,
            "model": model,
            "permissions": permissions,
            "view_only": view_only,
        }
        self._register.append((os.path.join(self.app_label, path), view, kw_models, kw))

    @property
    def views(self):
        yield from self._register

    @property
    def app(self):
        return {
            "name": self.name,
            "app_label": self.app_label,
            "app_url": f"/admin/{self.app_label}/",
            "has_module_perms": True,
            "models": [
                {**kw_models, "admin_url": f"/admin/{path}"}
                for path, _, kw_models, kw in self._register
            ],
        }


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
