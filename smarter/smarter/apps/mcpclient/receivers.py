"""Django Signal Receivers for mcpclient."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import MCPClient
from .serializers import MCPClientSerializer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])

module_prefix = __name__


@receiver(post_save, sender=MCPClient)
def mcpclient_saved(sender, instance: MCPClient, created: bool, **kwargs):
    """Create the default API for the mcpclient."""

    prefix = logging.formatted_text(f"{module_prefix}.mcpclient_saved()")
    data = logging.formatted_json(MCPClientSerializer(instance).data)
    if created:
        logger.info("%s - created %s, %s", prefix, instance, data)
    else:
        logger.info("%s - updated %s, %s", prefix, instance, data)


@receiver(pre_delete, sender=MCPClient)
def mcpclient_deleted(sender, instance: MCPClient, **kwargs):
    """Delete the default API for the mcpclient."""
    prefix = logging.formatted_text(f"{module_prefix}.mcpclient_deleted()")
    logger.info("%s - %s", prefix, instance)
