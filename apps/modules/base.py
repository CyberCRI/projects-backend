import inspect

from django.db import models


class AbstractModules:
    """abstract class for modules/queryset declarations"""

    def __init__(self, instance, /, user, **kw):
        self.instance = instance
        self.user = user

    def _items(self):
        members = inspect.getmembers(
            self,
            predicate=inspect.ismethod,
        )

        for name, func in members:
            # ignore private_method and "count" method (this method :D)
            if name.startswith("_") or name in ("count",):
                continue

            yield name, func

    def count(self):
        modules = {}
        for name, func in self._items():
            # func return queryset
            modules[name] = func().count()
        return modules


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
