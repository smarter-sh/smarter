"""Receiver functions for proxy signals."""

# pylint: disable=W0613


from django.dispatch import receiver
from rest_framework.request import Request

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .signals import broker_ready

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING])


@receiver(broker_ready)
def log_broker_ready(sender, request: Request, **kwargs):
    """Log when the broker is ready."""
    logger.info("Broker is ready", extra={"request": request})
