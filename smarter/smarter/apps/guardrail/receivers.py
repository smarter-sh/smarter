"""Django Signal Receivers for guardrail."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Guardrail
from .serializers import GuardrailSerializer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

module_prefix = __name__


@receiver(post_save, sender=Guardrail)
def guardrail_saved(sender, instance: Guardrail, created: bool, **kwargs):
    """Create the default API for the guardrail."""

    prefix = logging.formatted_text(f"{module_prefix}.guardrail_saved()")
    data = logging.formatted_json(GuardrailSerializer(instance).data)
    if created:
        logger.info("%s - created %s, %s", prefix, instance, data)
    else:
        logger.info("%s - updated %s, %s", prefix, instance, data)


@receiver(pre_delete, sender=Guardrail)
def guardrail_deleted(sender, instance: Guardrail, **kwargs):
    """Delete the default API for the guardrail."""
    prefix = logging.formatted_text(f"{module_prefix}.guardrail_deleted()")
    logger.info("%s - %s", prefix, instance)
