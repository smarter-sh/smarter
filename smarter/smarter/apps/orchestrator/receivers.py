"""Django Signal Receivers for orchestrator."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Orchestrator

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])

module_prefix = __name__


@receiver(post_save, sender=Orchestrator)
def orchestrator_saved(sender, instance: Orchestrator, created: bool, **kwargs):
    """
    Log the creation or update of an Orchestrator, with its name and id.

    Its serialized fields are not logged: they include the owner's user profile, whose
    email address is personal data.

    :param sender: The model class.
    :param instance: The Orchestrator that was saved.
    :param created: True if the Orchestrator was created, False if it was updated.
    """
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.orchestrator_saved()"
    if created:
        logger.info("%s created %s (id %s)", prefix, instance, instance.pk)
    else:
        logger.info("%s updated %s (id %s)", prefix, instance, instance.pk)


@receiver(pre_delete, sender=Orchestrator)
def orchestrator_deleted(sender, instance: Orchestrator, **kwargs):
    """
    Log that an Orchestrator is about to be deleted.

    :param sender: The model class.
    :param instance: The Orchestrator being deleted.
    """
    prefix = f"{logging.SmarterFormattedText.text(module_prefix)}.orchestrator_deleted()"
    logger.info("%s %s", prefix, instance)


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("Orchestrator", "orchestrator.Orchestrator", "orchestrator.OrchestratorHarness")
