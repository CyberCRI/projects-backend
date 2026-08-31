import inspect
from collections.abc import Callable
from functools import cache, wraps
from typing import Any

from django.db import models
from drf_spectacular.utils import OpenApiParameter

from apps.accounts.models import ProjectUser
from apps.commons.mixins import OrganizationRelated
from apps.organizations.models import Organization

IGNORE_MODULES_FUNCTION = "IGNORE_MODULES_FUNCTION"


def ignore_method(method):
    """ingore modules methods"""
    setattr(method, IGNORE_MODULES_FUNCTION, True)
    return method


class AbstractModules:
    """abstract class for modules/queryset declarations"""

    def __init__(
        self,
        instance,
        /,
        user: ProjectUser,
        organization: Organization | None = None,
        **kw,
    ):
        self.instance = instance
        # user instance needed to filter by user
        self.user = user
        # organization instance to filter elements by organization (optional)
        self.organization = organization

    @classmethod
    @ignore_method
    @cache
    def all_modules(cls) -> tuple[tuple[str, Callable]]:
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
    def modules(
        cls, modules_keys: tuple[str] | None = None
    ) -> tuple[tuple[str, Callable]]:
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


_modules: dict[type[models.Model], AbstractModules] = {}


def register_module(model: type[models.Model]):
    """decorator to register modules assoiate on models

    :param model: _description_
    """

    def _wrap(cls):
        _modules[model] = cls
        return cls

    return _wrap


def get_module(model: type[models.Model]) -> AbstractModules:
    """get regisered module"""
    return _modules[model]


def organization_related(func):
    """wraps method modules to filter by organization if organization is set"""

    @wraps(func)
    def _wrapped(_self: AbstractModules, *ar, **kw):
        qs: models.QuerySet[Any] = func(_self, *ar, **kw)
        model = qs.model

        assert issubclass(model, OrganizationRelated), (
            f"the decorator @organization_related need a queryset model extended by OrganizationRelated: model={model}"
        )

        # if organization is set in AbstractModule, filter by organizaton
        if _self.organization:
            return qs.filter(model.organization_query("", _self.organization))
        return qs

    return _wrapped
