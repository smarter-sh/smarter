"""Django Signal Receivers for llmhost."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import LLMHost, LLMHostCompute
from .models.compute import LLMHostComputeNodeGroupStatus
from .signals import llmhost_destroyed, llmhost_launch_failed, llmhost_launched

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING])


@receiver(llmhost_launch_failed, dispatch_uid="llmhost_launch_failed")
def llmhost_launch_failed_receiver(sender, llmhost: LLMHost, error: str = "", **kwargs):
    """
    Log that an LLMHost could not be launched, and why.

    The error is one that :class:`~smarter.apps.llmhost.services.LLMHostService` also records as the
    LLMHost's status message and event: a refused budget, or the cluster's or the cloud's error.

    :param sender: The class that sent the signal, the LLMHost service.
    :param llmhost: The LLMHost that was not launched.
    :param error: Why.
    :param kwargs: Other signal arguments (unused).
    """
    logger.warning("could not launch %s: %s", llmhost, error)


@receiver(llmhost_launched, dispatch_uid="llmhost_launched")
def llmhost_launched_receiver(sender, llmhost: LLMHost, resources=None, **kwargs):
    """
    Log that an LLMHost was launched, and the resources it was launched with.

    :param sender: The class that sent the signal, the LLMHost service.
    :param llmhost: The launched LLMHost.
    :param resources: A summary of the resources that were created or found.
    :param kwargs: Other signal arguments (unused).
    """
    logger.info("launched %s: %s", llmhost, resources)


@receiver(llmhost_destroyed, dispatch_uid="llmhost_destroyed")
def llmhost_destroyed_receiver(sender, llmhost: LLMHost, purge: bool = False, **kwargs):
    """
    Log that an LLMHost was destroyed.

    :param sender: The class that sent the signal, the LLMHost service.
    :param llmhost: The destroyed LLMHost.
    :param purge: True if its model volume was deleted too.
    :param kwargs: Other signal arguments (unused).
    """
    logger.info("destroyed %s, purge=%s", llmhost, purge)


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
