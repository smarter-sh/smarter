"""
Models for the vectorstore app.
"""

import logging

from django.db import models

from smarter.lib.django import waffle
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .vectorstore_meta import VectorestoreMeta


# pylint: disable=unused-argument
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class VectorstoreInterface(TimestampedModel):
    """
    Model representing the VectorstoreInterface configuration for a vector database.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Vectorstore Interface"
        verbose_name_plural = "Vectorstore Interfaces"

    vectorestore_meta = models.OneToOneField(
        VectorestoreMeta,
        help_text="The associated VectorestoreMeta object for this VectorstoreInterface configuration.",
        on_delete=models.CASCADE,
        related_name="vectorstore_interface",
    )

    text_key = models.CharField(
        help_text="The key in the vector database where the original text is stored, if applicable.",
        max_length=255,
        blank=True,
        null=True,
    )
    namespace = models.CharField(
        help_text="The namespace to use for the vector database, if applicable.",
        max_length=255,
        blank=True,
        null=True,
    )
    distance_strategy = models.CharField(
        help_text="The distance strategy to use for similarity search (e.g., cosine, euclidean, dot_product), if applicable.",
        max_length=50,
        blank=True,
        null=True,
    )
