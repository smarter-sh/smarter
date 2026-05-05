"""
Connection models utils
"""

from typing import Union

from smarter.apps.account.models import User
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .api_connection import ApiConnection
from .sql_connection import SqlConnection

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])
logger_prefix = formatted_text(f"{__name__}")


def get_cached_connection_detail_view_and_kind(
    user: User, kind: SAMKinds, name: str, invalidate: bool = False
) -> Union[ApiConnection, SqlConnection]:
    """
    Return a single instance of a concrete subclass of :class:`ConnectionBase` by name and kind.

    This method retrieves a connection object (such as :class:`SqlConnection` or :class:`ApiConnection`)
    for the given user, connection kind, and connection name. It searches across all concrete subclasses
    of :class:`ConnectionBase` and returns the matching instance if found.

    :param user: The user whose connection should be retrieved.
    :type user: User
    :param kind: The kind of connection (e.g., ``SAMKinds.SQL_CONNECTION`` or ``SAMKinds.API_CONNECTION``).
    :type kind: SAMKinds
    :param name: The name of the connection to retrieve.
    :type name: str
    :return: The connection instance if found, otherwise None.
    :rtype: Union[ApiConnection, SqlConnection]

    **Example:**

    .. code-block:: python

        sql_conn = ConnectionBase.get_cached_connection_detail_view_and_kind(user, SAMKinds.SQL_CONNECTION, "hr_database")
        api_conn = ConnectionBase.get_cached_connection_detail_view_and_kind(user, SAMKinds.API_CONNECTION, "inventory_api")

    See also:

    - :class:`SqlConnection`
    - :class:`ApiConnection`
    - :func:`smarter.lib.cache.cache_results`
    - :func:`smarter.apps.account.utils.get_cached_account_for_user`
    """

    logger.debug("%s.get_cached_connection_detail_view_and_kind: Retrieving connection for user_id=%s, kind=%s, name=%s, invalidate=%s", logger_prefix, user.id if user else None, kind, name, invalidate)  # type: ignore[union-attr]

    @cache_results()
    def cached_sqlconnection_by_id_and_name(account_id: int, name: str) -> Union["SqlConnection", None]:
        try:
            return (
                SqlConnection.objects.prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
                .get(user_profile__account__id=account_id, name=name)
            )
        except SqlConnection.DoesNotExist:
            return None

    @cache_results()
    def cached_apiconnection_by_id_and_name(account_id: int, name: str) -> Union["ApiConnection", None]:
        try:
            return (
                ApiConnection.objects.prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
                .get(user_profile__account__id=account_id, name=name)
            )
        except ApiConnection.DoesNotExist:
            return None

    account = get_cached_account_for_user(invalidate=False, user=user)
    if not kind or not kind in [SAMKinds.SQL_CONNECTION, SAMKinds.API_CONNECTION]:
        raise SmarterValueError(f"Unsupported connection kind: {kind}")
    if kind == SAMKinds.SQL_CONNECTION:
        try:
            if invalidate:
                cached_sqlconnection_by_id_and_name.invalidate(account.id, name)  # type: ignore[union-attr]
            return cached_sqlconnection_by_id_and_name(account.id, name)  # type: ignore[return-value]
        except SqlConnection.DoesNotExist:
            pass

    elif kind == SAMKinds.API_CONNECTION:
        try:
            if invalidate:
                cached_apiconnection_by_id_and_name.invalidate(account.id, name)  # type: ignore[union-attr]
            return cached_apiconnection_by_id_and_name(account.id, name)  # type: ignore[return-value]
        except ApiConnection.DoesNotExist:
            pass

    raise SmarterValueError(f"No connection found for user {user} with name '{name}' and kind '{kind}'")
