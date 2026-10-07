# pylint: disable=W0613,W0212
"""
Cache management utilities for MCPClient objects.

This module provides functions for efficient type-annotated retrieval and
caching of MCPClient querysets. It includes utilities to:

- Retrieve and cache MCPClients owned by a user profile
- Retrieve and cache MCPClients shared with a user profile
- Retrieve and cache MCPClients available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available MCPClients
- Invalidate all MCPClient-related caches for a user profile

Functions:

    - get_cached_mcpclients_owned_by_user_profile(user_profile)
    - invalidate_cached_mcpclients_owned_by_user_profile(user_profile)
    - get_cached_mcpclients_shared_with_user_profile(user_profile)
    - invalidate_cached_mcpclients_shared_with_user_profile(user_profile)
    - get_cached_mcpclients_available_to_user_profile(user_profile)
    - invalidate_cached_mcpclients_available_to_user_profile(user_profile)
    - invalidate_all_cached_mcpclients_for_user_profile(user_profile)
    - get_cached_catalog(mcpclient, refresh=False)
    - invalidate_cached_catalog(mcpclient)

MCP server catalogs, i.e. each server's tools, instructions and capabilities, are cached
for the MCPClient's ``cache_ttl`` seconds, so that prompts do not connect to the server
to list its tools. The cache key includes :attr:`MCPClient.fingerprint`, so that changing
how the MCPClient connects, or what it allows, invalidates its catalog. A failure to
connect is cached for :data:`FAILURE_CACHE_TTL` seconds, so that an unreachable server
does not delay every prompt by its timeout.

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.mcpclient.models.MCPClient
    - smarter.apps.mcpclient.serializers.MCPClientSerializer
"""

from typing import Optional

from django.core.cache import cache
from django.db import models
from django.utils import timezone

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .connection import MCPServerCatalog, MCPServerConnection, is_tool_allowed
from .exceptions import SmarterMCPClientConnectionError
from .models import MCPClient, MCPConnectionStatus
from .serializers import MCPClientSerializer
from .signals import mcpclient_connected, mcpclient_connection_failed

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_mcpclients_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[MCPClient]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = MCPClient.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching MCPClients: %s",
        logger_prefix,
        logging.formatted_json(MCPClientSerializer(retval, many=True).data),
    )
    return retval


def get_cached_mcpclients_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[MCPClient]:
    """
    Retrieve the MCPClients owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of MCPClient objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned MCPClients should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the MCPClient objects owned by the user.
    :rtype: QuerySet[MCPClient]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> mcpclients = get_cached_mcpclients_owned_by_user_profile(user_profile)
        >>> for bot in mcpclients:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_mcpclients_owned_by_user_profile` - Invalidate the cache for owned MCPClients of a user profile.
    """

    return _get_cached_mcpclients_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_mcpclients_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_mcpclients_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_mcpclients_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[MCPClient]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = MCPClient.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching MCPClients: %s",
        logger_prefix,
        logging.formatted_json(MCPClientSerializer(retval, many=True).data),
    )
    return retval


def get_cached_mcpclients_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[MCPClient]:
    """
    Retrieve the MCPClients shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of MCPClient objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared MCPClients should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the MCPClient objects shared with the user.
    :rtype: QuerySet[MCPClient]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_mcpclients = get_cached_mcpclients_shared_with_user_profile(user_profile)
        >>> for bot in shared_mcpclients:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_mcpclients_shared_with_user_profile` - Invalidate the cache for shared MCPClients of a user profile.
    """

    return _get_cached_mcpclients_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_mcpclients_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_mcpclients_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_mcpclients_available_to_user_profile(user_profile_id) -> models.QuerySet[MCPClient]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = MCPClient.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching MCPClients: %s",
        logger_prefix,
        logging.formatted_json(MCPClientSerializer(retval, many=True).data),
    )
    return retval


def get_cached_mcpclients_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[MCPClient]:
    """
    Retrieve the MCPClients available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of MCPClient objects that are available to the specified user profile,
    which may include both owned and shared MCPClients. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available MCPClients should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the MCPClient objects available to the user.
    :rtype: QuerySet[MCPClient]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_mcpclients = get_cached_mcpclients_available_to_user_profile(user_profile)
        >>> for bot in available_mcpclients:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_mcpclients_available_to_user_profile` - Invalidate the cache for available MCPClients of a user profile.
    """

    return _get_cached_mcpclients_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_mcpclients_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_mcpclients_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_mcpclients_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached MCPClient querysets related to the given UserProfile.

    This function invalidates the caches for all MCPClient querysets that are related to the specified user profile,
    including owned, shared, and available MCPClients. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached MCPClient querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_mcpclients_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_mcpclients_owned_by_user_profile` - Invalidate the cache for owned MCPClients of a user profile.
        - :func:`invalidate_cached_mcpclients_shared_with_user_profile` - Invalidate the cache for shared MCPClients of a user profile.
        - :func:`invalidate_cached_mcpclients_available_to_user_profile` - Invalidate the cache for available MCPClients of a user profile.
    """
    invalidate_cached_mcpclients_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_mcpclients_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_mcpclients_available_to_user_profile(user_profile=user_profile)


# -----------------------------------------------------------------------------
# MCP server catalogs
# -----------------------------------------------------------------------------
CATALOG_CACHE_PREFIX = "smarter.apps.mcpclient.catalog"
FAILURE_CACHE_TTL = 60
"""Seconds to remember that an MCP server could not be reached."""


def catalog_cache_key(mcpclient: MCPClient) -> str:
    """
    Return the cache key of an MCPClient's catalog.

    :param mcpclient: The MCPClient.
    :returns: A key that changes whenever the MCPClient's connection settings change.
    """
    return f"{CATALOG_CACHE_PREFIX}.{mcpclient.id}.{mcpclient.fingerprint}"  # type: ignore[attr-defined]


def failure_cache_key(mcpclient: MCPClient) -> str:
    """Return the cache key of an MCPClient's most recent connection failure."""
    return catalog_cache_key(mcpclient) + ".failure"


def record_connection(mcpclient: MCPClient, catalog: MCPServerCatalog) -> None:
    """
    Record a successful connection in the MCPClient's status fields.

    The fields are updated with a queryset update, which neither changes ``updated_at``
    nor sends ``post_save``, because this is a status change, not a configuration change.

    :param mcpclient: The MCPClient.
    :param catalog: What the MCP server reported.
    """
    values = {
        "status": MCPConnectionStatus.CONNECTED,
        "protocol_version": (catalog.protocol_version or "")[:16] or None,
        "server_name": (catalog.server_name or "")[:255] or None,
        "server_version": (catalog.server_version or "")[:64] or None,
        "tools": [tool.name for tool in catalog.tools if is_tool_allowed(mcpclient, tool.name)],
        "last_connected_at": timezone.now(),
        "last_error": None,
    }
    MCPClient.objects.filter(pk=mcpclient.pk).update(**values)
    for key, value in values.items():
        setattr(mcpclient, key, value)


def record_connection_failure(mcpclient: MCPClient, error: str) -> None:
    """
    Record a failed connection in the MCPClient's status fields.

    :param mcpclient: The MCPClient.
    :param error: A description of the error.
    """
    values = {"status": MCPConnectionStatus.ERROR, "last_error": error[:2000]}
    MCPClient.objects.filter(pk=mcpclient.pk).update(**values)
    for key, value in values.items():
        setattr(mcpclient, key, value)


def get_cached_catalog(mcpclient: MCPClient, refresh: bool = False) -> MCPServerCatalog:
    """
    Return an MCPClient's catalog: its MCP server's tools, instructions and capabilities.

    The catalog is cached for the MCPClient's ``cache_ttl`` seconds. On a cache miss,
    Smarter connects to the server, records the result in the MCPClient's status fields,
    and sends :data:`~smarter.apps.mcpclient.signals.mcpclient_connected` or
    :data:`~smarter.apps.mcpclient.signals.mcpclient_connection_failed`.

    :param mcpclient: The MCPClient.
    :param refresh: Connect to the server even if the catalog, or a recent failure, is cached.
    :returns: The catalog.
    :rtype: MCPServerCatalog
    :raises SmarterMCPClientConnectionError: If the server cannot be reached, now or, unless
        ``refresh``, within the last :data:`FAILURE_CACHE_TTL` seconds.
    :raises SmarterMCPClientConfigurationError: If the MCPClient is misconfigured.
    """
    key = catalog_cache_key(mcpclient)
    if not refresh and mcpclient.cache_ttl:
        data: Optional[dict] = cache.get(key)
        if data:
            logger.debug("%s.get_cached_catalog() cache hit for %s", logger_prefix, mcpclient.name)
            return MCPServerCatalog.from_dict(data)
        failure: Optional[str] = cache.get(failure_cache_key(mcpclient))
        if failure:
            raise SmarterMCPClientConnectionError(failure)

    try:
        catalog = MCPServerConnection(mcpclient).discover()
    except SmarterMCPClientConnectionError as e:
        record_connection_failure(mcpclient, e.message)
        if mcpclient.cache_ttl:
            cache.set(failure_cache_key(mcpclient), e.message, min(FAILURE_CACHE_TTL, mcpclient.cache_ttl))
        mcpclient_connection_failed.send(sender=get_cached_catalog, mcpclient=mcpclient, error=e.message)
        raise

    record_connection(mcpclient, catalog)
    if mcpclient.cache_ttl:
        cache.set(key, catalog.to_dict(), mcpclient.cache_ttl)
        cache.delete(failure_cache_key(mcpclient))
    mcpclient_connected.send(sender=get_cached_catalog, mcpclient=mcpclient, catalog=catalog)
    return catalog


def invalidate_cached_catalog(mcpclient: MCPClient) -> None:
    """
    Invalidate an MCPClient's cached catalog, and any cached connection failure.

    Catalogs cached under a previous :attr:`MCPClient.fingerprint` are no longer used,
    and expire with their ``cache_ttl``.

    :param mcpclient: The MCPClient.
    """
    cache.delete_many([catalog_cache_key(mcpclient), failure_cache_key(mcpclient)])
