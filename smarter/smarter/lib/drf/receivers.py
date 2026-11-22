# pylint: disable=unused-argument
"""Django signal receivers of API keys (SmarterAuthToken) and of token authentication events."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from rest_framework.exceptions import AuthenticationFailed

from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import SmarterAuthToken, invalidate_cached_auth_tokens
from .signals import (
    smarter_token_authentication_failure,
    smarter_token_authentication_request,
    smarter_token_authentication_success,
)


def should_log(level: int) -> bool:
    """
    Return whether this module logs, which it does while the ``RECEIVER_LOGGING`` waffle switch is active.

    :param level: The log level, which is ignored.
    :returns: True if the switch is active.
    """
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


logger = logging.getSmarterLogger(__name__, condition_func=should_log)


@receiver(post_save, sender=SmarterAuthToken)
def handle_auth_token_save(sender, instance, created, **kwargs):
    """
    Invalidate the user's cached API keys, and log the saved SmarterAuthToken at DEBUG.

    :param sender: The SmarterAuthToken model.
    :param instance: The saved token.
    :param created: True if the token was created.
    :param kwargs: The rest of the signal's arguments.
    """
    # the user's cached API keys, by the key's name, and by its old name after a rename.
    old_name = getattr(instance, "_loaded_name", None)
    invalidate_cached_auth_tokens(instance.user_id, names=(instance.name, old_name))
    logger.debug(
        "SmarterAuthToken: %s, created: %s",
        instance,
        created,
    )


@receiver(post_delete, sender=SmarterAuthToken)
def handle_smarter_auth_token_delete(sender, instance, **kwargs):
    """
    Invalidate the user's cached API keys, and log the deleted SmarterAuthToken at DEBUG.

    :param sender: The SmarterAuthToken model.
    :param instance: The deleted token.
    :param kwargs: The rest of the signal's arguments.
    """
    invalidate_cached_auth_tokens(instance.user_id, names=(instance.name,))
    logger.debug(
        "SmarterAuthToken: %s",
        instance,
    )


@receiver(smarter_token_authentication_request)
def handle_smarter_token_authentication_request(sender, token, url, **kwargs):
    """
    Log a token authentication request, at DEBUG.

    :param sender: The class that sent the signal.
    :param token: The masked token.
    :param url: The request's url.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.debug(
        "sender: %s, token: %s, url: %s",
        sender,
        token,
        url,
    )


@receiver(smarter_token_authentication_success)
def handle_smarter_token_authentication_success(sender, user, token, **kwargs):
    """
    Log a successful token authentication, at DEBUG.

    :param sender: The class that sent the signal.
    :param user: The authenticated user.
    :param token: The masked token.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.debug(
        "sender: %s, user: %s, token: %s",
        sender,
        user,
        token,
    )


@receiver(smarter_token_authentication_failure)
def handle_smarter_token_authentication_failure(sender, user, token, error: AuthenticationFailed, **kwargs):
    """
    Log a failed token authentication, as a warning.

    :param sender: The class that sent the signal.
    :param user: The user, usually anonymous.
    :param token: The masked token.
    :param error: The authentication error.
    :param kwargs: The rest of the signal's arguments.
    """
    logger.warning(
        "sender: %s, user: %s, token: %s, error: %s",
        sender,
        user,
        token,
        str(error),
    )


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("SmarterAuthToken", "drf.SmarterAuthToken", "llmclient.LLMClientAPIKey")
