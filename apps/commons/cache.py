from django.conf import settings
from django.core.cache import cache
from django.db import models
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


def redis_cache_view(
    key_prefix: str = "cache", timeout: int = 60 * settings.CACHE_DEFAULT_TTL
):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if settings.ENABLE_CACHE:
                key = f"{key_prefix}.{request.build_absolute_uri()}"
                if key in cache.keys("*"):  # noqa: SIM118
                    return Response(cache.get(key))
                response = func(request, *args, **kwargs)
                cache.set(key, response.data, timeout)
                return response
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def clear_cache_with_key(key_prefix: str):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if request.method != "GET" and settings.ENABLE_CACHE:
                cache.delete_many(cache.keys(f"{key_prefix}*"))
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def redis_cache_model_method(key_suffix: str):
    def decorator(func):
        def wrapper(instance, *args, **kwargs):
            if settings.ENABLE_CACHE:
                key = f"{instance.__class__.__name__}.{instance.pk}.{key_suffix}"
                if key in cache.keys("*"):  # noqa: SIM118
                    return cache.get(key)
                response = func(instance, *args, **kwargs)
                cache.set(key, response)
                return response
            return func(instance, *args, **kwargs)

        return wrapper

    return decorator


def clear_redis_cache_model_method(instance: models.Model, key_suffix: str = ""):
    if settings.ENABLE_CACHE:
        cache.delete_many(
            cache.keys(f"{instance.__class__.__name__}.{instance.pk}.{key_suffix}*")
        )


def redis_cache_viewset_method(
    key_prefix: str, timeout: int = 60 * settings.CACHE_DEFAULT_TTL
):
    def decorator(func):
        def wrapper(view: GenericViewSet, *args, **kwargs):
            if settings.ENABLE_CACHE:
                user = view.request.user.id
                uri = view.request.build_absolute_uri()
                key = f"{key_prefix}.{user}.{uri}"
                if key in cache.keys("*"):  # noqa: SIM118
                    return cache.get(key)
                response = func(view, *args, **kwargs)
                cache.set(key, response, timeout)
                return response
            return func(view, *args, **kwargs)

        return wrapper

    return decorator
