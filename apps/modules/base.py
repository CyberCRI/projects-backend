import inspect
from collections.abc import Callable
from functools import cache

from django.db import models
from drf_spectacular.utils import OpenApiParameter

IGNORE_MODULES_FUNCTION = "IGNORE_MODULES_FUNCTION"


def ignore_method(method):
    """ingore modules methods"""
    setattr(method, IGNORE_MODULES_FUNCTION, True)
    return method


class AbstractModules:
    """abstract class for modules/queryset declarations"""

    def __init__(self, instance, /, user, **kw):
        self.instance = instance
        self.user = user

    @classmethod
    @ignore_method
    @cache
    def all_modules(cls) -> tuple[str, Callable]:
        modules_list = []

        def predicate(item):
            return inspect.ismethod(item) or inspect.isfunction(item)

        members = inspect.getmembers(cls, predicate=predicate)

        for name, func in members:
            # ignore private_method and all method ignored
            if name.startswith("_") or getattr(func, IGNORE_MODULES_FUNCTION, False):
                continue

            modules_list.append((name, func))

        return tuple(modules_list)

    @classmethod
    @ignore_method
    @cache
    def modules(cls, modules_keys: tuple[str] | None = None) -> tuple[str, Callable]:
        modules_list = []

        for name, func in cls.all_modules():

            # yield only keys are set or all keys needed
            if modules_keys is None or name in modules_keys:
                modules_list.append((name, func))

        return tuple(modules_list)

    @ignore_method
    def count(self, modules_keys: tuple[str] | None = None):
        modules = {}
        for name, method in type(self).modules(modules_keys):
            # method is one modules (class method and not instance method)
            modules[name] = method(self).count()
        return modules

    @classmethod
    @ignore_method
    def ApiParameter(cls, **kw):  # noqa: N802
        """generate OpenApiParameter from modules class"""
        enum = [name for name, _ in cls.modules()]
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
