"""chatbot utils"""

from functools import wraps
from urllib.parse import urlparse

from django.core.cache import cache
from django.core.handlers.wsgi import WSGIRequest

from smarter.apps.account.models import Account
from smarter.apps.account.utils import get_cached_account_for_user


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
    """
    Caches the result of a function based on the request URI and user identifier.
    Associates a Smarter user account number with the cache key if the user is authenticated.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request: WSGIRequest, *args, **kwargs):
            uri = urlparse(request.build_absolute_uri()).path
            user_identifier = request.user.username if request.user and request.user.is_authenticated else "anonymous"
            account: Account = get_cached_account_for_user(request.user)
            if account:
                user_identifier = account.account_number
            cache_key = f"{func.__name__}_{uri}_{user_identifier}"
            result = cache.get(cache_key)
            if result is None:
                result = func(request, *args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator
