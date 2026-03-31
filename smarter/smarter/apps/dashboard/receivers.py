# pylint: disable=W0613
"""Dashboard app signal receivers."""

import logging

from django.dispatch import receiver

from smarter.apps.account.signals import cache_invalidate
from smarter.apps.dashboard.context_processors import cache_invalidations
from smarter.common.helpers.console_helpers import formatted_text_blue

logger = logging.getLogger(__name__)
module_prefix = "dashboard.receivers"


@receiver(cache_invalidate)
def cache_invalidation_receiver(sender, *args, **kwargs):
    """Signal receiver for cache invalidation."""
    user_profile = kwargs.get("user_profile")
    logger.info(
        "%s received cache_invalidate signal for %s with kwargs: %s",
        formatted_text_blue(f"{module_prefix}.cache_invalidation_receiver()"),
        user_profile,
        kwargs,
    )
    cache_invalidations(user_profile=user_profile)
