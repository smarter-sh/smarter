"""Django Signal Receivers for llmhost."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import LLMHost, LLMHostCompute
from .models.compute import LLMHostComputeNodeGroupStatus

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])


@receiver(post_save, sender=LLMHost)
def llmhost_saved(sender, instance: LLMHost, created: bool, **kwargs):
    """
    Log that an LLMHost was created or updated, with its name and id.

    Its serialized fields are not logged: they include the owner's user profile, whose
    email address is personal data.

    :param sender: The LLMHost model.
    :param instance: The LLMHost that was saved.
    :param created: Whether it was created, rather than updated.
    """

    if created:
        logger.info("created %s (id %s)", instance, instance.pk)
    else:
        logger.info("updated %s (id %s)", instance, instance.pk)


@receiver(pre_delete, sender=LLMHost)
def llmhost_deleted(sender, instance: LLMHost, **kwargs):
    """
    Log that an LLMHost is about to be deleted.

    :param sender: The LLMHost model.
    :param instance: The LLMHost being deleted.
    """
    logger.info("%s", instance)


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

    if instance.nodegroup_status == LLMHostComputeNodeGroupStatus.ABSENT:
        return
    try:
        ComputeProvisioner().delete_nodegroup(instance)
        logger.info("deleted the node group of %s", instance)
    except LLMHostComputeError as e:
        logger.error("the node group of %s was not deleted: %s", instance, e)


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("LLMHost", "llmhost.LLMHost", "llmhost.LLMHostCompute")
connect_listview_cache("LLMHostCompute", "llmhost.LLMHostCompute", "llmhost.LLMHost")
