"""Receiver functions for proxy signals."""

# pylint: disable=W0613

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .caching import invalidate_all_cached_proxies_for_user_profile
from .models import Proxy
from .signals import broker_ready, proxy_request_completed, proxy_request_failed

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING, SmarterWaffleSwitches.PROXY_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@receiver(broker_ready)
def log_broker_ready(sender, broker, **kwargs):
    """
    Log when the broker is ready.

    :param sender: The signal's sender.
    :param broker: The Proxy broker.
    """
    logger.debug("%s %s is ready", logger_prefix, broker)


@receiver(proxy_request_completed)
def log_proxy_request_completed(sender, proxy, user_profile, method, path, status, usage, elapsed, **kwargs):
    """
    Log each request that a Proxy forwarded.

    :param sender: The signal's sender.
    :param proxy: The Proxy.
    :param user_profile: The caller's user profile.
    :param method: The HTTP method.
    :param path: The provider API path.
    :param status: The provider's HTTP status code.
    :param usage: The token usage that the response reported.
    :param elapsed: The seconds that the forward took.
    """
    logger.debug(
        "%s Proxy %s forwarded %s %s for %s: %s in %.2fs, usage %s",
        logger_prefix,
        proxy.name,
        method,
        path,
        user_profile,
        status,
        elapsed,
        usage,
    )


@receiver(proxy_request_failed)
def log_proxy_request_failed(sender, proxy, user_profile, method, path, error, elapsed, **kwargs):
    """
    Log each request that a Proxy refused, or could not forward.

    :param sender: The signal's sender.
    :param proxy: The Proxy.
    :param user_profile: The caller's user profile.
    :param method: The HTTP method.
    :param path: The provider API path.
    :param error: The error.
    :param elapsed: The seconds until the failure.
    """
    logger.debug("%s Proxy %s failed %s %s for %s: %s", logger_prefix, proxy.name, method, path, user_profile, error)


@receiver(post_save, sender=Proxy)
@receiver(post_delete, sender=Proxy)
def invalidate_proxy_caches(sender, instance: Proxy, **kwargs):
    """
    Invalidate the owner's cached Proxy lists, which the web console's list view uses.

    A failure is logged as a warning, not raised.

    :param sender: The model class.
    :param instance: The Proxy that was saved or deleted.
    """
    try:
        invalidate_all_cached_proxies_for_user_profile(user_profile=instance.user_profile)
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("%s failed to invalidate the cached proxies of %s: %s", logger_prefix, instance, e)


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("Proxy", "proxy.Proxy", "provider.Provider", "secret.Secret")
