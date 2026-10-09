from typing import cast

from django.conf import settings
from django.core.cache import cache as django_cache
from django.db import models
from django_redis.cache import RedisCache
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

# Returned by `cache.get` on a cache miss, so cached `None` values are still hits
_MISSING = object()

# The default cache is django-redis: typed access to its extra methods
# (e.g. `delete_pattern`), unknown to Django's generic cache type
cache = cast(RedisCache, django_cache)


def redis_cache_view(
    key_prefix: str = "cache", timeout: int = 60 * settings.CACHE_DEFAULT_TTL
):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if settings.ENABLE_CACHE:
                key = f"{key_prefix}.{request.build_absolute_uri()}"
                cached = cache.get(key, _MISSING)
                if cached is not _MISSING:
                    return Response(cached)
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
                cache.delete_pattern(f"{key_prefix}*")
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def redis_cache_model_method(key_suffix: str):
    def decorator(func):
        def wrapper(instance, *args, **kwargs):
            if settings.ENABLE_CACHE:
                key = f"{instance.__class__.__name__}.{instance.pk}.{key_suffix}"
                cached = cache.get(key, _MISSING)
                if cached is not _MISSING:
                    return cached
                response = func(instance, *args, **kwargs)
                cache.set(key, response)
                return response
            return func(instance, *args, **kwargs)

        return wrapper

    return decorator


def clear_redis_cache_model_method(instance: models.Model, key_suffix: str = ""):
    if settings.ENABLE_CACHE:
        cache.delete_pattern(
            f"{instance.__class__.__name__}.{instance.pk}.{key_suffix}*"
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
                cached = cache.get(key, _MISSING)
                if cached is not _MISSING:
                    return cached
                response = func(view, *args, **kwargs)
                cache.set(key, response, timeout)
                return response
            return func(view, *args, **kwargs)

        return wrapper

    return decorator
