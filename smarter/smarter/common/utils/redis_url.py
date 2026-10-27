"""
Helpers for Redis urls.

Smarter keeps several things in one Redis server, each in its own numbered database, so
that clearing one can't delete another: the Celery broker in 0, the Django cache in 1 and
user sessions in 2. See ``CACHES`` and ``CELERY_BROKER_URL`` in :mod:`smarter.settings.base`.
"""

from urllib.parse import urlsplit, urlunsplit


def redis_url_with_database(url: str, database: int) -> str:
    """
    Return a Redis url for another database on the same server.

    :param url: A Redis url, e.g. ``redis://:secret@smarter-redis:6379/1``.
    :param database: The number of the database, e.g. ``2``.
    :returns: The url with its database replaced, e.g. ``redis://:secret@smarter-redis:6379/2``.
        The credentials, host, port and query string are kept.
    """
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{database}", parts.query, parts.fragment))


__all__ = ["redis_url_with_database"]
