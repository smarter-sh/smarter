"""Django Signal Receivers for orchestrator."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Orchestrator
from .serializers import OrchestratorSerializer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])

module_prefix = __name__


@receiver(post_save, sender=Orchestrator)
def orchestrator_saved(sender, instance: Orchestrator, created: bool, **kwargs):
    """Create the default API for the orchestrator."""

    prefix = logging.formatted_text(f"{module_prefix}.orchestrator_saved()")
    data = logging.formatted_json(OrchestratorSerializer(instance).data)
    if created:
        logger.info("%s - created %s, %s", prefix, instance, data)
    else:
        logger.info("%s - updated %s, %s", prefix, instance, data)


@receiver(pre_delete, sender=Orchestrator)
def orchestrator_deleted(sender, instance: Orchestrator, **kwargs):
    """Delete the default API for the orchestrator."""
    prefix = logging.formatted_text(f"{module_prefix}.orchestrator_deleted()")
    logger.info("%s - %s", prefix, instance)
