"""Django Signal Receivers for llmhost."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import LLMHost, LLMHostCompute
from .models.compute import LLMHostComputeNodeGroupStatus
from .serializers import LLMHostSerializer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])

module_prefix = __name__


@receiver(post_save, sender=LLMHost)
def llmhost_saved(sender, instance: LLMHost, created: bool, **kwargs):
    """Create the default API for the llmhost."""

    prefix = logging.formatted_text(f"{module_prefix}.llmhost_saved()")
    data = logging.formatted_json(LLMHostSerializer(instance).data)
    if created:
        logger.info("%s - created %s, %s", prefix, instance, data)
    else:
        logger.info("%s - updated %s, %s", prefix, instance, data)


@receiver(pre_delete, sender=LLMHost)
def llmhost_deleted(sender, instance: LLMHost, **kwargs):
    """Delete the default API for the llmhost."""
    prefix = logging.formatted_text(f"{module_prefix}.llmhost_deleted()")
    logger.info("%s - %s", prefix, instance)


@receiver(pre_delete, sender=LLMHostCompute)
def llmhost_compute_deleted(sender, instance: LLMHostCompute, **kwargs):
    """
    Delete the compute's node group, and its nodes.

    A compute that LLMHosts use cannot be deleted:
    the foreign key protects it.
    """
    # pylint: disable=import-outside-toplevel
    from .services.compute import ComputeProvisioner
    from .services.exceptions import LLMHostComputeError

    prefix = logging.formatted_text(f"{module_prefix}.llmhost_compute_deleted()")
    if instance.nodegroup_status == LLMHostComputeNodeGroupStatus.ABSENT:
        return
    try:
        ComputeProvisioner().delete_nodegroup(instance)
        logger.info("%s - deleted the node group of %s", prefix, instance)
    except LLMHostComputeError as e:
        logger.error("%s - the node group of %s was not deleted: %s", prefix, instance, e)
