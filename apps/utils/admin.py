import os

from django.views import View


class ExtraAdminMixins:
    """Mixins to convert view to admin custom View"""

    admin_site = None
    admin_app = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx = ctx | self.admin_site.each_context(self.request)
        ctx |= self.admin_app or {}
        return ctx


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
