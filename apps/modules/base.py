import inspect

from django.db import models
from drf_spectacular.utils import OpenApiParameter


class AbstractModules:
    """abstract class for modules/queryset declarations"""

    def __init__(self, instance, /, user, **kw):
        self.instance = instance
        self.user = user

    @classmethod
    def _items(cls, modules_keys: list[str] | None = None):

        def predicate(item):
            return inspect.ismethod(item) or inspect.isfunction(item)

        members = inspect.getmembers(cls, predicate=predicate)

        for name, func in members:
            # ignore private_method and "count" method (this method :D)
            if name.startswith("_") or name in ("count", "ApiParameter"):
                continue

            # yield only keys are set or all keys needed
            if modules_keys is None or name in modules_keys:
                yield name, func

    def count(self, modules_keys: list[str] | None = None):
        modules = {}
        for name, method in self._items(modules_keys):
            # method is one modules (class method and not instance method)
            modules[name] = method(self).count()
        return modules

    @classmethod
    def ApiParameter(cls, **kw):  # noqa: N802
        """generate OpenApiParameter from modules class"""
        enum = [name for name, _ in cls._items()]
        return OpenApiParameter(
            name="modules",
            description="modules keys to returns",
            required=False,
            type=str,
            many=True,
            enum=enum,
            default=None,
            **kw,
        )


_modules: dict[models.Model] = {}


def register_module(model: models.Model):
    """decorator to register modules assoiate on models

    :param model: _description_
    """

    def _wrap(cls):
        _modules[model] = cls
        return cls

    return _wrap


def get_module(model: models.Model):
    """get regisered module"""
    return _modules[model]
