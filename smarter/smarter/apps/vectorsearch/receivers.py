"""Django Signal Receivers for vectorsearch."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Vectorsearch
from .signals import vectorsearch_called

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING])


@receiver(vectorsearch_called, dispatch_uid="vectorsearch_called")
def vectorsearch_called_receiver(sender, vectorsearch: Vectorsearch, **kwargs):
    """
    Log that a Vectorsearch is about to run.

    :param sender: The class that sent the signal, e.g. the Vectorsearch api view.
    :param vectorsearch: The Vectorsearch that was called.
    :param kwargs: Other signal arguments: ``request``, ``args`` and ``kwargs`` (unused).
    """
    logger.info("running vectorsearch %s", vectorsearch.pk)


@receiver(post_save, sender=Vectorsearch)
def vectorsearch_saved(sender, instance: Vectorsearch, created: bool, **kwargs):
    """
    Log the creation or update of a Vectorsearch, with its name and id.

    Its serialized fields are not logged: they include the owner's user profile, whose
    email address is personal data.

    :param sender: The model class.
    :param instance: The Vectorsearch that was saved.
    :param created: True if the Vectorsearch was created, False if it was updated.
    """
    if created:
        logger.info("created %s (id %s)", instance, instance.pk)
    else:
        logger.info("updated %s (id %s)", instance, instance.pk)


@receiver(pre_delete, sender=Vectorsearch)
def vectorsearch_deleted(sender, instance: Vectorsearch, **kwargs):
    """
    Log that a Vectorsearch is about to be deleted.

    :param sender: The model class.
    :param instance: The Vectorsearch being deleted.
    """
    logger.info("%s", instance)


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("Vectorsearch", "vectorsearch.Vectorsearch")
