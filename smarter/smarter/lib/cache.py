"""chatbot utils"""

from functools import wraps

from django.core.cache import cache


def cache_results(timeout=60 * 60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            url = args[1] if len(args) > 1 else kwargs.get("url")
            cache_key = f"chatbot_get_by_url_{url}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator
