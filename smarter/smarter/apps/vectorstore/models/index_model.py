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


class IndexModelInterface(TimestampedModel):
    """
    Model representing the SAMIndexModelInterface configuration for a vector database.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Index Model Interface"
        verbose_name_plural = "Index Model Interfaces"

    vectorestore_meta = models.OneToOneField(
        VectorestoreMeta,
        help_text="The associated VectorestoreMeta object for this IndexModelInterface configuration.",
        on_delete=models.CASCADE,
        related_name="index_model_interface",
    )
    spec = models.JSONField(
        help_text="Index deployment spec. Accepts a dict, ServerlessSpec, PodSpec, or ByocSpec. Example: ServerlessSpec(cloud=CloudProvider.AWS, region=AwsRegion.US_EAST_1)",
        default=dict,
        blank=True,
        null=True,
    )
    dimension = models.IntegerField(
        help_text="Number of dimensions for the index. Must be between 1 and 20,000, or None. Example: 1536.",
        default=None,
        blank=True,
        null=True,
    )
    metric = models.CharField(
        help_text="Distance metric for similarity search. Accepts Metric enum or string. Default: 'cosine'.",
        max_length=50,
        default="cosine",
        blank=True,
        null=True,
    )
    timeout = models.IntegerField(
        help_text="Timeout in seconds for index operations. Must be greater than zero or None.",
        default=None,
        blank=True,
        null=True,
    )
    deletion_protection = models.CharField(
        help_text="Deletion protection setting. Accepts DeletionProtection enum or string. Default: 'disabled'.",
        max_length=50,
        default=None,
        blank=True,
        null=True,
    )
    vector_type = models.CharField(
        help_text="Type of vector. Accepts VectorType enum or string. Default: 'dense'.",
        max_length=50,
        default=None,
        blank=True,
        null=True,
    )
