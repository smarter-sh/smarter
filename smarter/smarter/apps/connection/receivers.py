# pylint: disable=W0613
"""Django signal receivers for connection app."""

import logging
from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from requests import Response

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.console_helpers import formatted_json, formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import AbstractBroker

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
    broker_ready,
    sql_connection_attempted,
    sql_connection_failed,
    sql_connection_query_attempted,
    sql_connection_query_failed,
    sql_connection_query_success,
    sql_connection_success,
    sql_connection_validated,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

prefix = formatted_text(__name__)


# ------------------------------------------------------------------------------
# Django model receivers.
# ------------------------------------------------------------------------------
@receiver(post_save, sender=ApiConnection)
def handle_api_connection_saved(sender, instance, created, **kwargs):
    """Handle API connection saved signal."""

    if created:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() ApiConnection() created"),
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s",
            formatted_text(prefix + "post_save() ApiConnection() updated"),
            formatted_json(model_to_dict(instance)),
        )


@receiver(post_save, sender=SqlConnection)
def handle_sql_connection_saved(sender, instance: SqlConnection, created, **kwargs):
    """Handle SQL connection saved signal."""

    user_profile = str(instance.user_profile) if instance.user_profile else "(user_profile is missing)"
    if created:
        logger.info(
            "%s - %s %s",
            formatted_text(prefix + "post_save() SqlConnection() created"),
            user_profile,
            formatted_json(model_to_dict(instance)),
        )
    else:
        logger.info(
            "%s - %s %s",
            formatted_text(prefix + "post_save() SqlConnection() updated"),
            user_profile,
            formatted_json(model_to_dict(instance)),
        )


def masked_dict(dic: dict) -> dict:
    """Mask sensitive data in a dictionary."""
    masked = dic.copy()
    if "PASSWORD" in masked:
        masked["PASSWORD"] = "********"
    return masked


@receiver(sql_connection_attempted, dispatch_uid="sql_connection_attempted")
def handle_sql_connection_attempted(sender, connection: SqlConnection, **kwargs):
    """Handle SQL connection attempted signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "sql_connection_attempted()"),
        connection.get_connection_string(),
    )


@receiver(sql_connection_success, dispatch_uid="sql_connection_success")
def handle_sql_connection_success(sender, connection: SqlConnection, **kwargs):
    """Handle SQL connection success signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "sql_connection_success()"),
        connection.get_connection_string(),
    )


@receiver(sql_connection_validated, dispatch_uid="sql_connection_validated")
def handle_sql_connection_validated(sender, connection: SqlConnection, **kwargs):
    """Handle SQL connection validated signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "sql_connection_validated()"),
        connection.get_connection_string(),
    )


@receiver(sql_connection_failed, dispatch_uid="sql_connection_failed")
def handle_sql_connection_failed(sender, connection: SqlConnection, error: str, **kwargs):
    """Handle SQL connection failed signal."""

    logger.error(
        "%s - %s - error: %s",
        formatted_text(prefix + "sql_connection_failed()"),
        connection.get_connection_string(masked=not smarter_settings.debug_mode),
        error,
    )

    raise SmarterConfigurationError(
        f"Remote SQL Connection {connection.get_connection_string(masked=not smarter_settings.debug_mode)} failed: {error}"
    ) from None


@receiver(sql_connection_query_attempted, dispatch_uid="sql_connection_query_attempted")
def handle_sql_connection_query_attempted(sender, connection: SqlConnection, sql: str, limit: int, **kwargs):
    """Handle SQL connection query attempted signal."""

    logger.info(
        "%s - %s - sql: %s - limit: %s",
        formatted_text(prefix + "sql_connection_query_attempted()"),
        connection.get_connection_string(),
        sql,
        limit,
    )


@receiver(sql_connection_query_success, dispatch_uid="sql_connection_query_success")
def handle_sql_connection_query_success(sender, connection: SqlConnection, sql: str, limit: int, **kwargs):
    """Handle SQL connection query success signal."""

    logger.info(
        "%s - %s - sql: %s - limit: %s",
        formatted_text(prefix + "sql_connection_query_success()"),
        connection.get_connection_string(),
        sql,
        limit,
    )


@receiver(sql_connection_query_failed, dispatch_uid="sql_connection_query_failed")
def handle_sql_connection_query_failed(sender, connection: SqlConnection, sql: str, limit: int, error: str, **kwargs):
    """Handle SQL connection query failed signal."""

    logger.info(
        "%s - %s - sql: %s - limit: %s - error: %s",
        formatted_text(prefix + "sql_connection_query_failed()"),
        connection.get_connection_string(),
        sql,
        limit,
        error,
    )

    raise SmarterConfigurationError(
        f"Remote SQL {connection.get_connection_string()} query execution failed {sql}: {error}"
    )


@receiver(api_connection_attempted, dispatch_uid="api_connection_attempted")
def handle_api_connection_attempted(sender, connection: ApiConnection, **kwargs):
    """Handle API connection attempted signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "api_connection_attempted()"),
        connection.get_connection_string(),
    )


@receiver(api_connection_success, dispatch_uid="api_connection_success")
def handle_api_connection_success(sender, connection: ApiConnection, **kwargs):
    """Handle API connection success signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "api_connection_success()"),
        connection.get_connection_string(),
    )


@receiver(api_connection_failed, dispatch_uid="api_connection_failed")
def handle_api_connection_failed(sender, connection: ApiConnection, error: Optional[Exception] = None, **kwargs):
    """Handle API connection failed signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "api_connection_failed()"),
        connection.get_connection_string(),
    )


@receiver(api_connection_query_attempted, dispatch_uid="api_connection_query_attempted")
def handle_api_connection_query_attempted(sender, connection: ApiConnection, **kwargs):
    """Handle API connection query attempted signal."""

    logger.info(
        "%s - %s",
        formatted_text(prefix + "api_connection_query_attempted()"),
        connection.get_connection_string(),
    )


@receiver(api_connection_query_success, dispatch_uid="api_connection_query_success")
def handle_api_connection_query_success(
    sender, connection: ApiConnection, response: Optional[Response] = None, **kwargs
):
    """Handle API connection query success signal."""

    logger.info(
        "%s - %s - response: %s",
        formatted_text(prefix + "api_connection_query_success()"),
        connection.get_connection_string(),
        formatted_json(response.json()) if response else None,
    )


@receiver(api_connection_query_failed, dispatch_uid="api_connection_query_failed")
def handle_api_connection_query_failed(
    sender, connection: ApiConnection, response: Optional[Response] = None, error: Optional[Exception] = None, **kwargs
):
    """Handle API connection query failed signal."""

    logger.info(
        "%s - %s - response: %s - error: %s",
        formatted_text(prefix + "api_connection_query_failed()"),
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
        "%s - %s deleting.",
        formatted_text(prefix + "ApiConnection().pre_delete()"),
        instance,
    )


@receiver(pre_delete, sender=SqlConnection)
def handle_sql_connection_pre_delete(sender, instance, **kwargs):
    """Handle pre-delete signal for SqlConnection."""
    logger.info(
        "%s - %s deleting.",
        formatted_text(prefix + "SqlConnection().pre_delete()"),
        instance,
    )


@receiver(broker_ready, dispatch_uid="broker_ready")
def handle_broker_ready(sender, broker: AbstractBroker, **kwargs):
    """Handle broker ready signal."""

    logger.info(
        "%s %s %s for %s is ready.",
        formatted_text(f"{prefix}broker_ready()"),
        broker.kind,
        str(broker),
        broker.name,
    )
