import abc

from django.db.models import Model

from .logger import logger


class _NOSET: ...


# TODO create a new Cache class to optimize save/get with
# prefetch all model/data needed


class BaseCache(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save(self, instance, *fields): ...

    @abc.abstractmethod
    def save_m2m(self, instance, *fields): ...

    @abc.abstractmethod
    def model(self, model, *fields): ...


class LiveCache(BaseCache):
    def save(self, obj, **fields):
        """save obj if field are changed"""
        updated = False
        for field, value in fields.items():
            if getattr(obj, field, _NOSET) == value:
                continue

            setattr(obj, field, value)
            updated = True

        if updated or not obj.pk:
            logger.debug("Save object %s", obj)
            obj.save()

    def save_m2m(self, obj, **fields) -> False:
        """this method checks all pk m2m linked to the obj, if is a diff, we "set" all needed_pk"""
        for name, value in fields.items():
            getattr(obj, name).set(value)

    def model(self, model: Model, **fields):
        try:
            return model.objects.get(**fields)
        except model.DoesNotExist:
            return model(**fields)
