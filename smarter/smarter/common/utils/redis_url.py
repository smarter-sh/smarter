"""
Helpers for Redis urls.

Smarter keeps several things in one Redis server, each in its own numbered database, so
that clearing one can't delete another: the Celery broker in 0, the Django cache in 1 and
user sessions in 2. See ``CACHES`` and ``CELERY_BROKER_URL`` in :mod:`smarter.settings.base`.
"""

from typing import Optional
from urllib.parse import quote, urlsplit, urlunsplit


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


def redis_server_url(host_and_port: str, username: Optional[str], password: str) -> str:
    """
    Return the url of a Redis server, with a user's credentials and no database.

    Both are quoted, so that a character that a url reserves, such as ``@`` or ``%``, can't end
    the credentials early. Without a username, the url authenticates as Redis's ``default`` user.

    :param host_and_port: The server, e.g. ``smarter-redis:6379``.
    :param username: The Redis ACL user, e.g. ``tools``, or None for the ``default`` user.
    :param password: The user's password.
    :returns: The url, e.g. ``redis://tools:secret@smarter-redis:6379``. Append ``/<database>``.
    """
    quoted_password = quote(password, safe="")
    user = ""
    if username:
        user = quote(username, safe="")
    url = f"redis://{user}:{quoted_password}@{host_and_port}"
    return url


__all__ = ["redis_server_url", "redis_url_with_database"]
