from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response


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
