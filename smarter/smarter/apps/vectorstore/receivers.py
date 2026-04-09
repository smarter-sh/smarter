# pylint: disable=unused-argument
"""
Receivers for the vectorstore app.
"""

import json
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.apps.vectorstore.models import VectorDatabase
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)
module_prefix = f"{__name__}"


@receiver(post_save, sender=VectorDatabase)
def account_post_save(sender: VectorDatabase, instance: VectorDatabase, created, **kwargs):
    """Signal receiver for created/saved of VectorDatabase model."""
    model_prefix = formatted_text(f"{module_prefix}.account_post_save()")
    account_json = json.dumps(model_to_dict(instance))
    if created:
        logger.info("%s VectorDatabase created: %s", model_prefix, account_json)
    else:
        logger.info("%s VectorDatabase updated: %s", model_prefix, account_json)
        logger.info(
            "%s invalidating cache for VectorDatabase: %s",
            formatted_text(f"{module_prefix}.account_post_save()"),
            instance,
        )
        VectorDatabase.get_cached_object(invalidate=True, pk=instance.pk)


@receiver(post_delete, sender=VectorDatabase)
def account_post_delete(sender: VectorDatabase, instance: VectorDatabase, **kwargs):
    """Signal receiver for deleted of VectorDatabase model."""
    model_prefix = formatted_text(f"{module_prefix}.account_post_delete()")
    account_json = json.dumps(model_to_dict(instance))
    logger.info("%s VectorDatabase deleted: %s", model_prefix, account_json)
    logger.info(
        "%s invalidating cache for deleted VectorDatabase: %s",
        formatted_text(f"{module_prefix}.account_post_delete()"),
        instance,
    )
    VectorDatabase.get_cached_object(invalidate=True, pk=instance.pk)
