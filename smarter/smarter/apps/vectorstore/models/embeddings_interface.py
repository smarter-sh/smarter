"""
Models for the vectorstore app.
"""

import logging

from django.db import models

from smarter.apps.provider.models import Provider, ProviderModel
from smarter.common.exceptions import SmarterValueError
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


class EmbeddingsInterface(TimestampedModel):
    """
    Model representing the SAMEmbeddingsInterface configuration for a vector database.
    """

    vectorestore_meta = models.OneToOneField(
        VectorestoreMeta,
        help_text="The associated VectorestoreMeta object for this EmbeddingsInterface configuration.",
        on_delete=models.CASCADE,
        related_name="embeddings_interface",
    )
    provider = models.ForeignKey(
        Provider,
        help_text="The provider associated with this vector database.",
        on_delete=models.CASCADE,
        related_name="vector_databases",
    )
    provider_model = models.ForeignKey(
        ProviderModel,
        help_text="The provider model associated with this vector database.",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vector_databases",
    )
    config = models.JSONField(
        help_text="Additional configuration settings for the embeddings interface.",
        default=dict,
        blank=True,
        null=True,
    )
    dimensions = models.IntegerField(
        help_text="Number of embedding dimensions.",
        blank=True,
        null=True,
    )
    deployment = models.CharField(
        help_text="Deployment name or model name.",
        max_length=255,
        blank=True,
        null=True,
    )
    api_version = models.CharField(
        help_text="OpenAI API version.",
        max_length=50,
        blank=True,
        null=True,
    )
    base_url = models.CharField(
        help_text="Base URL for OpenAI API.",
        max_length=255,
        blank=True,
        null=True,
    )
    openai_api_type = models.CharField(
        help_text="OpenAI API type.",
        max_length=50,
        blank=True,
        null=True,
    )
    openai_api_proxy = models.CharField(
        help_text="Proxy URL for OpenAI API.",
        max_length=255,
        blank=True,
        null=True,
    )
    embedding_ctx_length = models.IntegerField(
        help_text="Embedding context length.",
        default=8191,
        blank=True,
        null=True,
    )
    api_key = models.CharField(
        help_text="OpenAI API key or secret reference.",
        max_length=255,
        blank=True,
        null=True,
    )
    organization = models.CharField(
        help_text="OpenAI organization ID.",
        max_length=255,
        blank=True,
        null=True,
    )
    allowed_special = models.JSONField(
        help_text="Allowed special tokens (set[str] or 'all').",
        default=dict,
        blank=True,
        null=True,
    )
    disallowed_special = models.JSONField(
        help_text="Disallowed special tokens (set, sequence, or 'all').",
        default=dict,
        blank=True,
        null=True,
    )
    chunk_size = models.IntegerField(
        help_text="Chunk size for embedding requests.",
        default=1000,
        blank=True,
        null=True,
    )
    max_retries = models.IntegerField(
        help_text="Maximum number of retries for API calls.",
        default=2,
        blank=True,
        null=True,
    )
    timeout = models.FloatField(
        help_text="Timeout for API requests (float, tuple, or other).",
        blank=True,
        null=True,
    )
    headers = models.JSONField(
        help_text="Custom headers for API requests.",
        default=dict,
        blank=True,
        null=True,
    )
    tiktoken_enabled = models.BooleanField(
        help_text="Enable tiktoken for tokenization.",
        default=True,
        blank=True,
        null=True,
    )
    tiktoken_model_name = models.CharField(
        help_text="Tiktoken model name.",
        max_length=255,
        blank=True,
        null=True,
    )
    show_progress_bar = models.BooleanField(
        help_text="Show progress bar during embedding.",
        default=False,
        blank=True,
        null=True,
    )
    model_kwargs = models.JSONField(
        help_text="Additional model keyword arguments.",
        default=dict,
        blank=True,
        null=True,
    )
    skip_empty = models.BooleanField(
        help_text="Skip empty inputs.",
        default=False,
        blank=True,
        null=True,
    )
    default_headers = models.JSONField(
        help_text="Default headers for API requests.",
        default=dict,
        blank=True,
        null=True,
    )
    default_query = models.JSONField(
        help_text="Default query parameters for API requests.",
        default=dict,
        blank=True,
        null=True,
    )
    retry_min_seconds = models.IntegerField(
        help_text="Minimum seconds between retries.",
        default=4,
        blank=True,
        null=True,
    )
    retry_max_seconds = models.IntegerField(
        help_text="Maximum seconds between retries.",
        default=20,
        blank=True,
        null=True,
    )
    check_ctx_length = models.BooleanField(
        help_text="Check embedding context length.",
        default=True,
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        """
        Override the save method to include validation for the embeddings provider model's
        embedding support.
        """

        if self.provider_model is not None and not self.provider_model.supports_embedding:
            raise SmarterValueError(
                f"The embeddings provider model {self.provider_model} does not support embedding, which is required for vector databases."
            )

        return super().save(*args, **kwargs)
