# pylint: disable=W0613
"""Django signal receivers for connection app."""

from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from requests import Response

from smarter.common.helpers.console_helpers import formatted_json, formatted_text
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

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])

prefix = formatted_text(__name__) + "."


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------
@receiver(post_save, sender=ApiConnection)
def handle_api_connection_saved(sender, instance, created, **kwargs):
    """Handle API connection saved signal."""

    logger.info(
        "%shandle_api_connection_saved() ApiConnection %s %s",
        prefix,
        instance.name,
        "created" if created else "updated",
    )
    # the whole row is only for a developer tracing a flow, and formatted_json() is costly.
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%shandle_api_connection_saved() %s", prefix, formatted_json(model_to_dict(instance)))


@receiver(post_save, sender=SqlConnection)
def handle_sql_connection_saved(sender, instance: SqlConnection, created, **kwargs):
    """Handle SQL connection saved signal."""

    user_profile = str(instance.user_profile) if instance.user_profile else "(user_profile is missing)"
    logger.info(
        "%shandle_sql_connection_saved() SqlConnection %s %s for %s",
        prefix,
        instance.name,
        "created" if created else "updated",
        user_profile,
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%shandle_sql_connection_saved() %s", prefix, formatted_json(model_to_dict(instance)))


def masked_dict(dic: SmarterDictType) -> SmarterDictType:
    """Mask sensitive data in a dictionary."""
    masked = dic.copy()
    if "PASSWORD" in masked:
        masked["PASSWORD"] = "********"
    return masked


@receiver(sql_connection_attempted, dispatch_uid="sql_connection_attempted")
def handle_sql_connection_attempted(sender, connection: SqlConnection, **kwargs):
    """Handle SQL connection attempted signal."""

    logger.info(
        "%s %s",
        prefix + "sql_connection_attempted()",
        connection.get_connection_string(),
    )


@receiver(sql_connection_success, dispatch_uid="sql_connection_success")
def handle_sql_connection_success(sender, connection: SqlConnection, **kwargs):
    """Handle SQL connection success signal."""

    logger.info(
        "%s %s is %s",
        prefix + "sql_connection_success()",
        connection.get_connection_string(),
        SmarterReadyState.READY,
    )


@receiver(sql_connection_validated, dispatch_uid="sql_connection_validated")
def handle_sql_connection_validated(sender, connection: SqlConnection, **kwargs):
    """Handle SQL connection validated signal."""

    logger.info(
        "%s %s",
        prefix + "sql_connection_validated()",
        connection.get_connection_string(),
    )


@receiver(sql_connection_failed, dispatch_uid="sql_connection_failed")
def handle_sql_connection_failed(sender, connection: SqlConnection, error: str, **kwargs):
    """
    Handle SQL connection failed signal.

    Only logs the failure: the method that sent the signal reports it to its caller, by returning
    None. The connection string is always masked, so that its password is never logged.
    """

    logger.error(
        "%s %s is %s - error: %s",
        prefix + "sql_connection_failed()",
        connection.get_connection_string(),
        SmarterReadyState.NOT_READY,
        error,
    )


@receiver(sql_connection_query_attempted, dispatch_uid="sql_connection_query_attempted")
def handle_sql_connection_query_attempted(sender, connection: SqlConnection, sql: str, limit: int, **kwargs):
    """Handle SQL connection query attempted signal."""

    logger.info(
        "%s %s - sql: %s - limit: %s",
        prefix + "sql_connection_query_attempted()",
        connection.get_connection_string(),
        sql,
        limit,
    )


@receiver(sql_connection_query_success, dispatch_uid="sql_connection_query_success")
def handle_sql_connection_query_success(sender, connection: SqlConnection, sql: str, limit: int, **kwargs):
    """Handle SQL connection query success signal."""

    logger.info(
        "%s %s - sql: %s - limit: %s",
        prefix + "sql_connection_query_success()",
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
        "%s %s - sql: %s - limit: %s - error: %s",
        prefix + "sql_connection_query_failed()",
        connection.get_connection_string(),
        sql,
        limit,
        error,
    )


@receiver(api_connection_attempted, dispatch_uid="api_connection_attempted")
def handle_api_connection_attempted(sender, connection: ApiConnection, **kwargs):
    """Handle API connection attempted signal."""

    logger.info(
        "%s %s",
        prefix + "api_connection_attempted()",
        connection.get_connection_string(),
    )


@receiver(api_connection_success, dispatch_uid="api_connection_success")
def handle_api_connection_success(sender, connection: ApiConnection, **kwargs):
    """Handle API connection success signal."""

    logger.info(
        "%s %s is %s",
        prefix + "api_connection_success()",
        connection.get_connection_string(),
        SmarterReadyState.READY,
    )


@receiver(api_connection_failed, dispatch_uid="api_connection_failed")
def handle_api_connection_failed(sender, connection: ApiConnection, error: Optional[Exception] = None, **kwargs):
    """Handle API connection failed signal."""

    logger.info(
        "%s %s is %s",
        prefix + "api_connection_failed()",
        connection.get_connection_string(),
        SmarterReadyState.NOT_READY,
    )


@receiver(api_connection_query_attempted, dispatch_uid="api_connection_query_attempted")
def handle_api_connection_query_attempted(sender, connection: ApiConnection, **kwargs):
    """Handle API connection query attempted signal."""

    logger.info(
        "%s %s",
        prefix + "api_connection_query_attempted()",
        connection.get_connection_string(),
    )


@receiver(api_connection_query_success, dispatch_uid="api_connection_query_success")
def handle_api_connection_query_success(
    sender, connection: ApiConnection, response: Optional[Response] = None, **kwargs
):
    """Handle API connection query success signal."""

    logger.info(
        "%s %s - response: %s",
        prefix + "api_connection_query_success()",
        connection.get_connection_string(),
        formatted_json(response.json()) if response else None,
    )


@receiver(api_connection_query_failed, dispatch_uid="api_connection_query_failed")
def handle_api_connection_query_failed(
    sender, connection: ApiConnection, response: Optional[Response] = None, error: Optional[Exception] = None, **kwargs
):
    """Handle API connection query failed signal."""

    logger.info(
        "%s %s - response: %s - error: %s",
        prefix + "api_connection_query_failed()",
        connection.get_connection_string(),
        formatted_json(response.json()) if response else None,
        error,
    )


# ------------------------------------------------------------------------------
# pre_delete signals for
#    ApiConnection,
#    SqlConnection,
# ------------------------------------------------------------------------------


@receiver(pre_delete, sender=ApiConnection)
def handle_api_connection_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for ApiConnection."""
    logger.info(
        "%s %s deleting.",
        prefix + "ApiConnection().pre_delete()",
        instance,
    )


@receiver(pre_delete, sender=SqlConnection)
def handle_sql_connection_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for SqlConnection."""
    logger.info(
        "%s %s deleting.",
        prefix + "SqlConnection().pre_delete()",
        instance,
    )


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("Connection", "connection.ConnectionBase", "llmtool.PluginDataApi", "llmtool.PluginDataSql")
