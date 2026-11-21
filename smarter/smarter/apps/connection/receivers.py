# pylint: disable=W0613
"""Django signal receivers for connection app."""

from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from requests import Response

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .models import (
    ApiConnection,
    SqlConnection,
)
from .signals import (
    api_connection_attempted,
    api_connection_failed,
    api_connection_query_attempted,
    api_connection_query_failed,
    api_connection_query_success,
    api_connection_success,
    sql_connection_attempted,
    sql_connection_failed,
    sql_connection_query_attempted,
    sql_connection_query_failed,
    sql_connection_query_success,
    sql_connection_success,
    sql_connection_validated,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING, SmarterWaffleSwitches.CONNECTION_LOGGING]
)


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------
@receiver(post_save, sender=ApiConnection)
def handle_api_connection_saved(sender, instance, created, **kwargs):
    """
    Log that an ApiConnection was created or updated, and its whole row at DEBUG level.

    :param sender: The class that sent the signal.
    :param instance: The ApiConnection that was saved.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "ApiConnection %s %s",
        instance.name,
        "created" if created else "updated",
    )
    # the whole row is only for a developer tracing a flow, and SmarterFormattedText.json() is costly.
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", SmarterFormattedText.json(model_to_dict(instance)))


@receiver(post_save, sender=SqlConnection)
def handle_sql_connection_saved(sender, instance: SqlConnection, created, **kwargs):
    """
    Log that a SqlConnection was created or updated, and its whole row at DEBUG level.

    :param sender: The class that sent the signal.
    :param instance: The SqlConnection that was saved.
    :param created: True if the row was created, False if it was updated.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    user_profile = str(instance.user_profile) if instance.user_profile else "(user_profile is missing)"
    logger.info(
        "SqlConnection %s %s for %s",
        instance.name,
        "created" if created else "updated",
        user_profile,
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", SmarterFormattedText.json(model_to_dict(instance)))


def masked_dict(dic: SmarterDictType) -> SmarterDictType:
    """Mask sensitive data in a dictionary."""
    masked = dic.copy()
    if "PASSWORD" in masked:
        masked["PASSWORD"] = "********"
    return masked


@receiver(sql_connection_attempted, dispatch_uid="sql_connection_attempted")
def handle_sql_connection_attempted(sender, connection: SqlConnection, **kwargs):
    """
    Log a SQL connection attempt, with the masked connection string.

    :param sender: The class that sent the signal.
    :param connection: The SqlConnection.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s",
        connection.get_connection_string(),
    )


@receiver(sql_connection_success, dispatch_uid="sql_connection_success")
def handle_sql_connection_success(sender, connection: SqlConnection, **kwargs):
    """
    Log that a SQL connection succeeded and is ready.

    :param sender: The class that sent the signal.
    :param connection: The SqlConnection.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s is %s",
        connection.get_connection_string(),
        SmarterReadyState.READY,
    )


@receiver(sql_connection_validated, dispatch_uid="sql_connection_validated")
def handle_sql_connection_validated(sender, connection: SqlConnection, **kwargs):
    """
    Log that a SQL connection was validated.

    :param sender: The class that sent the signal.
    :param connection: The SqlConnection.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s",
        connection.get_connection_string(),
    )


@receiver(sql_connection_failed, dispatch_uid="sql_connection_failed")
def handle_sql_connection_failed(sender, connection: SqlConnection, error: str, **kwargs):
    """
    Handle SQL connection failed signal.

    Only logs the failure: the method that sent the signal reports it to its caller, by returning
    None. The connection string is always masked, so that its password is never logged.

    :param sender: The class that sent the signal.
    :param connection: The SqlConnection that failed.
    :param error: Why it failed.
    :param kwargs: Other signal arguments: ``stage``, what failed, e.g. ``"SSH connection"``.
    """
    stage = kwargs.get("stage", "connection")
    logger.error(
        "%s is %s - %s failed: %s",
        connection.get_connection_string(),
        SmarterReadyState.NOT_READY,
        stage,
        error,
    )


@receiver(sql_connection_query_attempted, dispatch_uid="sql_connection_query_attempted")
def handle_sql_connection_query_attempted(sender, connection: SqlConnection, sql: str, limit: int, **kwargs):
    """
    Log a SQL query attempt, with its SQL and row limit.

    :param sender: The class that sent the signal.
    :param connection: The SqlConnection.
    :param sql: The SQL query.
    :param limit: The row limit of the query.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s - sql: %s - limit: %s",
        connection.get_connection_string(),
        sql,
        limit,
    )


@receiver(sql_connection_query_success, dispatch_uid="sql_connection_query_success")
def handle_sql_connection_query_success(sender, connection: SqlConnection, sql: str, limit: int, **kwargs):
    """
    Log a successful SQL query, with its SQL and row limit.

    :param sender: The class that sent the signal.
    :param connection: The SqlConnection.
    :param sql: The SQL query.
    :param limit: The row limit of the query.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s - sql: %s - limit: %s",
        connection.get_connection_string(),
        sql,
        limit,
    )


@receiver(sql_connection_query_failed, dispatch_uid="sql_connection_query_failed")
def handle_sql_connection_query_failed(sender, connection: SqlConnection, sql: str, limit: int, error: str, **kwargs):
    """
    Handle SQL connection query failed signal.

    Only logs the failure: execute_query(), which sent the signal, reports it to its caller by
    returning False.
    """

    logger.error(
        "%s - sql: %s - limit: %s - error: %s",
        connection.get_connection_string(),
        sql,
        limit,
        error,
    )


@receiver(api_connection_attempted, dispatch_uid="api_connection_attempted")
def handle_api_connection_attempted(sender, connection: ApiConnection, **kwargs):
    """
    Log an API connection attempt.

    :param sender: The class that sent the signal.
    :param connection: The ApiConnection.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s",
        connection.get_connection_string(),
    )


@receiver(api_connection_success, dispatch_uid="api_connection_success")
def handle_api_connection_success(sender, connection: ApiConnection, **kwargs):
    """
    Log that an API connection succeeded and is ready.

    :param sender: The class that sent the signal.
    :param connection: The ApiConnection.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s is %s",
        connection.get_connection_string(),
        SmarterReadyState.READY,
    )


@receiver(api_connection_failed, dispatch_uid="api_connection_failed")
def handle_api_connection_failed(sender, connection: ApiConnection, error: Optional[Exception] = None, **kwargs):
    """
    Log, at INFO level, that an API connection failed and is not ready.

    :param sender: The class that sent the signal.
    :param connection: The ApiConnection.
    :param error: The exception, if any. It is not logged.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s is %s",
        connection.get_connection_string(),
        SmarterReadyState.NOT_READY,
    )


@receiver(api_connection_query_attempted, dispatch_uid="api_connection_query_attempted")
def handle_api_connection_query_attempted(sender, connection: ApiConnection, **kwargs):
    """
    Log an API query attempt.

    :param sender: The class that sent the signal.
    :param connection: The ApiConnection.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s",
        connection.get_connection_string(),
    )


@receiver(api_connection_query_success, dispatch_uid="api_connection_query_success")
def handle_api_connection_query_success(
    sender, connection: ApiConnection, response: Optional[Response] = None, **kwargs
):
    """
    Log a successful API query, with its JSON response body.

    :param sender: The class that sent the signal.
    :param connection: The ApiConnection.
    :param response: The HTTP response, or None.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s - response: %s",
        connection.get_connection_string(),
        SmarterFormattedText.json(response.json()) if response else None,
    )


@receiver(api_connection_query_failed, dispatch_uid="api_connection_query_failed")
def handle_api_connection_query_failed(
    sender, connection: ApiConnection, response: Optional[Response] = None, error: Optional[Exception] = None, **kwargs
):
    """
    Log, at INFO level, a failed API query, with its JSON response body and error.

    :param sender: The class that sent the signal.
    :param connection: The ApiConnection.
    :param response: The HTTP response, or None.
    :param error: The exception, or None.
    :param kwargs: Other keyword arguments sent with the signal.
    """

    logger.info(
        "%s - response: %s - error: %s",
        connection.get_connection_string(),
        SmarterFormattedText.json(response.json()) if response else None,
        error,
    )


# ------------------------------------------------------------------------------
# pre_delete signals for
#    ApiConnection,
#    SqlConnection,
# ------------------------------------------------------------------------------


@receiver(pre_delete, sender=ApiConnection)
def handle_api_connection_pre_delete(sender, instance, **kwargs):
    """
    Log that an ApiConnection is about to be deleted.

    :param sender: The class that sent the signal.
    :param instance: The ApiConnection being deleted.
    :param kwargs: Other keyword arguments sent with the signal.
    """
    logger.info(
        "ApiConnection %s deleting.",
        instance,
    )


@receiver(pre_delete, sender=SqlConnection)
def handle_sql_connection_pre_delete(sender, instance, **kwargs):
    """
    Log that a SqlConnection is about to be deleted.

    :param sender: The class that sent the signal.
    :param instance: The SqlConnection being deleted.
    :param kwargs: Other keyword arguments sent with the signal.
    """
    logger.info(
        "SqlConnection %s deleting.",
        instance,
    )


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("Connection", "connection.ConnectionBase", "llmtool.PluginDataApi", "llmtool.PluginDataSql")
