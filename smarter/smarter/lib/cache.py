"""chatbot utils"""

import logging
from functools import wraps
from urllib.parse import urlparse

from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest

from smarter.common.const import SMARTER_DEFAULT_CACHE_TIMEOUT


logger = logging.getLogger(__name__)


def cache_results(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            result = cache.get(cache_key)
            if result:
                logger.info("cache_results() cache hit for %s", cache_key)
            else:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator


def cache_request(timeout=SMARTER_DEFAULT_CACHE_TIMEOUT):
    """
    Caches the result of a function based on the request URI and user identifier.
    Associates a Smarter user account number with the cache key if the user is authenticated.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request: WSGIRequest, *args, **kwargs):
            parsed_url = urlparse(request.build_absolute_uri())
            url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            user_identifier = (
                request.user.username if hasattr(request, "user") and request.user.is_authenticated else "anonymous"
            )
            cache_key = f"{func.__name__}_{url}_{user_identifier}"
            result = cache.get(cache_key)
            if result:
                logger.info("cache_request() cache hit for %s", cache_key)
            else:
                result = func(request, *args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator
