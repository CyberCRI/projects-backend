import inspect
from collections.abc import Callable
from functools import cache

from django.db import models
from django.db.models import Count, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
from drf_spectacular.utils import OpenApiParameter

from apps.accounts.models import ProjectUser

IGNORE_MODULES_FUNCTION = "IGNORE_MODULES_FUNCTION"


def ignore_method(method):
    """ingore modules methods"""
    setattr(method, IGNORE_MODULES_FUNCTION, True)
    return method


class AbstractModules:
    """abstract class for modules/queryset declarations"""

    model: models.Model

    def __init__(
        self,
        instance: models.Model | OuterRef,
        /,
        user: ProjectUser,
        **kw,
    ):

        self.instance = instance
        self.user = user

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
    def outer_ref(self, queryset: QuerySet) -> QuerySet:
        if isinstance(self.instance, OuterRef):
            return queryset.annotate(**{self.instance.name: self.instance})
        return queryset

    @classmethod
    @ignore_method
    def annotate_subquery(
        cls,
        user: ProjectUser,
        instance: OuterRef,
        modules_keys: tuple[str] | None = None,
    ) -> dict[str, Subquery]:
        all_queries = {}

        instance = cls(instance, user)

        for name, method in cls.modules(modules_keys):

            qs = (
                method(instance)
                .annotate(__modules=Value("__modules"))
                .values("__modules")
                .order_by("__modules")
                .annotate(count=Count("__modules"))
                .values("count")[:1]
            )

            all_queries[name] = Coalesce(
                Subquery(qs, output_field=models.IntegerField()), 0
            )

        return all_queries

    @ignore_method
    def count(self, modules_keys: tuple[str] | None = None) -> dict[str, int]:

        return (
            self.model.objects.filter(pk=self.instance.pk)
            .annotate_modules(self.user, modules_keys, outout_key="modules")
            .values_list("modules", flat=True)
        )

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


_modules: dict[models.Model, AbstractModules] = {}


def register_module(model: models.Model):
    """decorator to register modules assoiate on models

    :param model: _description_
    """

    def _wrap(cls):
        _modules[model] = cls
        cls.model = model
        return cls

    return _wrap


def get_module(model: models.Model):
    """get regisered module"""
    return _modules[model]
