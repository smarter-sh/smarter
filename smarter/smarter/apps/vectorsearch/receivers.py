"""Django Signal Receivers for vectorsearch."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Vectorsearch
from .serializers import VectorsearchSerializer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING])

module_prefix = __name__


@receiver(post_save, sender=Vectorsearch)
def vectorsearch_saved(sender, instance: Vectorsearch, created: bool, **kwargs):
    """Create the default API for the vectorsearch."""

    prefix = logging.formatted_text(f"{module_prefix}.vectorsearch_saved()")
    data = logging.formatted_json(VectorsearchSerializer(instance).data)
    if created:
        logger.info("%s - created %s, %s", prefix, instance, data)
    else:
        logger.info("%s - updated %s, %s", prefix, instance, data)


@receiver(pre_delete, sender=Vectorsearch)
def vectorsearch_deleted(sender, instance: Vectorsearch, **kwargs):
    """Delete the default API for the vectorsearch."""
    prefix = logging.formatted_text(f"{module_prefix}.vectorsearch_deleted()")
    logger.info("%s - %s", prefix, instance)
