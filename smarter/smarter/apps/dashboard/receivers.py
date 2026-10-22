# pylint: disable=W0613
"""Dashboard app signal receivers."""

from django.dispatch import receiver

from smarter.apps.account.signals import cache_invalidate
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


@receiver(cache_invalidate)
def cache_invalidation_receiver(sender, *args, **kwargs):
    """Signal receiver for cache invalidation."""
    from smarter.apps.dashboard.context_processors import cache_invalidations

    user_profile = kwargs.get("user_profile")
    logger.debug(
        "%s.cache_invalidation_receiver() received cache_invalidate from %s for user profile %s",
        logger_prefix,
        getattr(sender, "__name__", sender),
        user_profile.id if user_profile else None,
    )
    cache_invalidations(user_profile=user_profile)
