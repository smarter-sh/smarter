"""chatbot utils"""

from functools import wraps
from urllib.parse import urlparse

from django.core.cache import cache


def cache_results(timeout=60 * 60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator


def cache_request(timeout=60 * 60):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            uri = urlparse(request.build_absolute_uri()).path
            cache_key = f"{func.__name__}_{uri}"
            result = cache.get(cache_key)
            if result is None:
                result = func(request, *args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator
