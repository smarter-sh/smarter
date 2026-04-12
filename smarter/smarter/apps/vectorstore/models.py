"""
Models for the vectorstore app.
"""

import logging
from typing import Optional

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    User,
    UserProfile,
)
from smarter.apps.account.utils import (
    SmarterCachedObjects,
    get_cached_admin_user_for_account,
)
from smarter.apps.connection.models import ApiConnection
from smarter.apps.provider.models import Provider, ProviderModel
from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=unused-argument
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class VectorDatabaseBackendKind(models.TextChoices):
    """
    Enum representing the supported backend kinds for the vector database.
    """

    QDRANT = (SmarterVectorStoreBackends.QDRANT.value, SmarterVectorStoreBackends.QDRANT.value)
    WEAVIATE = (SmarterVectorStoreBackends.WEAVIATE.value, SmarterVectorStoreBackends.WEAVIATE.value)
    PINECONE = (SmarterVectorStoreBackends.PINECONE.value, SmarterVectorStoreBackends.PINECONE.value)


class VectorDatabaseStatus(models.TextChoices):
    """
    Enum representing the possible statuses of the vector database.
    """

    PROVISIONING = ("provisioning", "Provisioning")
    READY = ("ready", "Ready")
    FAILED = ("failed", "Failed")
    DELETING = ("deleting", "Deleting")


class VectorDatabaseQuerySet(models.QuerySet):
    """
    Custom queryset for the VectorDatabase model.
    """

    def active(self):
        return self.filter(is_active=True)

    def ready(self):
        return self.filter(status=VectorDatabaseStatus.READY, is_active=True)


class VectorDatabaseManager(models.Manager):
    """
    Custom manager for the VectorDatabase model.
    """

    def get_queryset(self):
        return VectorDatabaseQuerySet(self.model, using=self._db)

    def create_with_defaults(self, **kwargs):
        kwargs.setdefault("status", VectorDatabaseStatus.PROVISIONING)
        return self.create(**kwargs)


class VectorDatabase(MetaDataWithOwnershipModel):
    """
    Model representing a vector database.
    """

    # --------------------------------------------------------------------------
    # Vectorstore Interface fields
    # --------------------------------------------------------------------------
    connection = models.ForeignKey(
        ApiConnection,
        help_text="The Smarter Connection object containing connection details for the vector database. If provided, this connection will be used instead of the host, port, auth_config, and password fields to establish the connection. The Connection object must be owned by the authenticated API user and must contain the necessary information to connect to the vector database.",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vector_databases",
    )
    backend = models.CharField(
        help_text="The backend type for the vector database (e.g., qdrant, weaviate, pinecone).",
        max_length=50,
        choices=VectorDatabaseBackendKind.choices,
        blank=False,
        null=False,
    )
    is_active = models.BooleanField(
        help_text="Indicates whether the vector database is active.",
        default=True,
        blank=True,
        null=False,
    )
    status = models.CharField(
        help_text="The current status of the vector database (e.g., provisioning, ready, failed, deleting).",
        max_length=50,
        choices=VectorDatabaseStatus.choices,
        default=VectorDatabaseStatus.PROVISIONING,
        blank=False,
        null=False,
    )

    # --------------------------------------------------------------------------
    # Vectorstore interface fields (from SAMVectorstoreInterface)
    # --------------------------------------------------------------------------
    vectorstore_text_key = models.CharField(
        help_text="The key in the vector database where the original text is stored, if applicable.",
        max_length=255,
        blank=True,
        null=True,
    )
    vectorstore_namespace = models.CharField(
        help_text="The namespace to use for the vector database, if applicable.",
        max_length=255,
        blank=True,
        null=True,
    )
    vectorstore_distance_strategy = models.CharField(
        help_text="The distance strategy to use for similarity search (e.g., cosine, euclidean, dot_product), if applicable.",
        max_length=50,
        blank=True,
        null=True,
    )

    # --------------------------------------------------------------------------
    # Index model fields
    # --------------------------------------------------------------------------
    index_model_spec = models.JSONField(
        help_text="Index deployment spec. Accepts a dict, ServerlessSpec, PodSpec, or ByocSpec. Example: ServerlessSpec(cloud=CloudProvider.AWS, region=AwsRegion.US_EAST_1)",
        default=dict,
        blank=True,
        null=True,
    )
    index_model_dimension = models.IntegerField(
        help_text="Number of dimensions for the index. Must be between 1 and 20,000, or None. Example: 1536.",
        default=None,
        blank=True,
        null=True,
    )
    index_model_metric = models.CharField(
        help_text="Distance metric for similarity search. Accepts Metric enum or string. Default: 'cosine'.",
        max_length=50,
        default="cosine",
        blank=True,
        null=True,
    )
    index_model_timeout = models.IntegerField(
        help_text="Timeout in seconds for index operations. Must be greater than zero or None.",
        default=None,
        blank=True,
        null=True,
    )
    index_model_deletion_protection = models.CharField(
        help_text="Deletion protection setting. Accepts DeletionProtection enum or string. Default: 'disabled'.",
        max_length=50,
        default=None,
        blank=True,
        null=True,
    )
    index_model_vector_type = models.CharField(
        help_text="Type of vector. Accepts VectorType enum or string. Default: 'dense'.",
        max_length=50,
        default=None,
        blank=True,
        null=True,
    )

    # --------------------------------------------------------------------------
    # Embeddings interface fields (from SAMEmbeddingsInterface)
    # --------------------------------------------------------------------------
    embeddings_provider = models.CharField(
        help_text="The name of a Smarter provider associated with this vector database and owned by the authenticated API user.",
        max_length=255,
        blank=False,
        null=False,
    )
    embeddings_provider_model = models.CharField(
        help_text="The name of a Smarter provider model related to the Smarter Provider. Example: 'text-embedding-ada-002'",
        max_length=255,
        blank=True,
        null=True,
    )
    embeddings_config = models.JSONField(
        help_text="Additional configuration settings for the embeddings interface.",
        default=dict,
        blank=True,
        null=True,
    )
    embeddings_provider = models.ForeignKey(
        Provider,
        help_text="The provider associated with this vector database.",
        on_delete=models.CASCADE,
        related_name="vector_databases",
    )
    embeddings_model = models.ForeignKey(
        ProviderModel,
        help_text="The provider model associated with this vector database.",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vector_databases",
    )
    embeddings_dimensions = models.IntegerField(
        help_text="Number of embedding dimensions.",
        blank=True,
        null=True,
    )
    embeddings_deployment = models.CharField(
        help_text="Deployment name or model name.",
        max_length=255,
        blank=True,
        null=True,
    )
    embeddings_api_version = models.CharField(
        help_text="OpenAI API version.",
        max_length=50,
        blank=True,
        null=True,
    )
    embeddings_base_url = models.CharField(
        help_text="Base URL for OpenAI API.",
        max_length=255,
        blank=True,
        null=True,
    )
    embeddings_api_type = models.CharField(
        help_text="OpenAI API type.",
        max_length=50,
        blank=True,
        null=True,
    )
    embeddings_proxy = models.CharField(
        help_text="Proxy URL for OpenAI API.",
        max_length=255,
        blank=True,
        null=True,
    )
    embeddings_ctx_length = models.IntegerField(
        help_text="Embedding context length.",
        default=8191,
        blank=True,
        null=True,
    )
    embeddings_api_key = models.CharField(
        help_text="OpenAI API key or secret reference.",
        max_length=255,
        blank=True,
        null=True,
    )
    embeddings_organization = models.CharField(
        help_text="OpenAI organization ID.",
        max_length=255,
        blank=True,
        null=True,
    )
    embeddings_allowed_special = models.JSONField(
        help_text="Allowed special tokens (set[str] or 'all').",
        default=dict,
        blank=True,
        null=True,
    )
    embeddings_disallowed_special = models.JSONField(
        help_text="Disallowed special tokens (set, sequence, or 'all').",
        default=dict,
        blank=True,
        null=True,
    )
    embeddings_chunk_size = models.IntegerField(
        help_text="Chunk size for embedding requests.",
        default=1000,
        blank=True,
        null=True,
    )
    embeddings_max_retries = models.IntegerField(
        help_text="Maximum number of retries for API calls.",
        default=2,
        blank=True,
        null=True,
    )
    embeddings_timeout = models.FloatField(
        help_text="Timeout for API requests (float, tuple, or other).",
        blank=True,
        null=True,
    )
    embeddings_headers = models.JSONField(
        help_text="Custom headers for API requests.",
        default=dict,
        blank=True,
        null=True,
    )
    embeddings_tiktoken_enabled = models.BooleanField(
        help_text="Enable tiktoken for tokenization.",
        default=True,
        blank=True,
        null=True,
    )
    embeddings_tiktoken_model_name = models.CharField(
        help_text="Tiktoken model name.",
        max_length=255,
        blank=True,
        null=True,
    )
    embeddings_show_progress_bar = models.BooleanField(
        help_text="Show progress bar during embedding.",
        default=False,
        blank=True,
        null=True,
    )
    embeddings_model_kwargs = models.JSONField(
        help_text="Additional model keyword arguments.",
        default=dict,
        blank=True,
        null=True,
    )
    embeddings_skip_empty = models.BooleanField(
        help_text="Skip empty inputs.",
        default=False,
        blank=True,
        null=True,
    )
    embeddings_default_headers = models.JSONField(
        help_text="Default headers for API requests.",
        default=dict,
        blank=True,
        null=True,
    )
    embeddings_default_query = models.JSONField(
        help_text="Default query parameters for API requests.",
        default=dict,
        blank=True,
        null=True,
    )
    embeddings_retry_min_seconds = models.IntegerField(
        help_text="Minimum seconds between retries.",
        default=4,
        blank=True,
        null=True,
    )
    embeddings_retry_max_seconds = models.IntegerField(
        help_text="Maximum seconds between retries.",
        default=20,
        blank=True,
        null=True,
    )
    embeddings_check_ctx_length = models.BooleanField(
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

        if self.embeddings_provider_model is not None and not self.embeddings_provider_model.supports_embedding:
            raise SmarterValueError(
                f"The embeddings provider model {self.embeddings_provider_model} does not support embedding, which is required for vector databases."
            )

        return super().save(*args, **kwargs)

    @classmethod
    def get_cached_object(cls, *args, backend: Optional[str] = None, **kwargs) -> "VectorDatabase":
        """
        Retrieve a cached VectorDatabase object based on the provided name and backend.
        This method is used to optimize backend retrieval by caching database objects.

        Args:
            backend (str): The backend kind of the vector database.
        Returns:
            VectorDatabase: The cached VectorDatabase object matching the name and backend.
        """

        @cache_results(cls.cache_expiration)
        def _get_object_by_name_and_backend(name: str, backend: str) -> "VectorDatabase":
            """
            Internal method to retrieve a model instance by primary key with caching.
            Prefetches related tags and selects related user profile, account, and
            user for optimal access. Handles most common SAM pk retrieval scenarios.

            :param name: The name of the vector database.
            :param backend: The backend kind of the vector database.

            :returns: The model instance if found, otherwise None.
            :rtype: Optional["VectorDatabase"]
            """
            try:
                retval = (
                    cls.objects.prefetch_related("tags")
                    .select_related("user_profile", "user_profile__account", "user_profile__user")
                    .get(name=name, backend=backend)
                )
                logger.debug(
                    "%s._get_object_by_pk() fetched %s - %s",
                    formatted_text(VectorDatabase.__name__ + ".get_cached_object()"),
                    type(retval).__name__,
                    str(retval),
                )
                return retval
            except cls.DoesNotExist:
                logger.debug(
                    "%s._get_object_by_name_and_backend() no %s object found for name: %s and backend: %s",
                    formatted_text(VectorDatabase.__name__ + ".get_cached_object()"),
                    cls.__name__,
                    name,
                    backend,
                )
                raise

        invalidate = kwargs.get("invalidate", False)
        name = kwargs.get("name")
        if name is not None and backend is not None:
            if invalidate:
                _get_object_by_name_and_backend.invalidate(name=name, backend=backend)
            return _get_object_by_name_and_backend(name=name, backend=backend)

        return super().get_cached_object(*args, **kwargs)  # type: ignore

    @classmethod
    def get_cached_vectorstores_for_user(cls, user: User, invalidate: bool = False) -> list["VectorDatabase"]:
        """
        Return a list of all instances of :class:`VectorDatabase`.

        This method retrieves all vector store objects associated with the user's account.
        It is useful for enumerating all available vector stores for a given user.

        :param user: The user whose vector stores should be retrieved.
        :type user: User
        :return: A list of all vector store instances for the user's account.
        :rtype: list[VectorDatabase]

        **Example:**

        .. code-block:: python

            vectorstores = VectorDatabase.get_cached_vectorstores_for_user(user)
            # returns [<VectorDatabase ...>, <VectorDatabase ...>, ...]

        See also:

        - :func:`smarter.apps.account.utils.get_cached_account_for_user`
        """

        if user is None:
            logger.warning("%s.get_cached_vectorstores_for_user: user is None", cls.formatted_class_name)
            return []
        user_profile = UserProfile.get_cached_object(invalidate=invalidate, user=user)
        admin_user = get_cached_admin_user_for_account(invalidate=invalidate, account=user_profile.cached_account)  # type: ignore
        admin_user_profile = UserProfile.get_cached_object(invalidate=invalidate, user=admin_user)  # type: ignore
        instances = []

        @cache_results()
        def get_cached_vectorstores_for_user_profile_id(pk: int) -> list["VectorDatabase"]:
            # create querysets for user_profile, account and smarter account.
            user_profile_qs = (
                cls.objects.filter(user_profile=user_profile)
                .prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
            )
            instances.extend(user_profile_qs)

            user_account_qs = (
                cls.objects.filter(user_profile=admin_user_profile)
                .prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
            )
            instances.extend(user_account_qs)

            smarter_account_qs = (
                cls.objects.filter(user_profile__account=SmarterCachedObjects.smarter_admin_user_profile)
                .prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
            )
            instances.extend(smarter_account_qs)

            logger.debug(
                "%s.get_cached_vectorstores_for_user: Found these vector stores %s for user %s",
                cls.formatted_class_name,
                instances,
                user,
            )
            unique_instances = {(instance.__class__, instance.pk): instance for instance in instances}.values()
            return list(unique_instances)

        if invalidate:
            get_cached_vectorstores_for_user_profile_id.invalidate(pk=user_profile.id)  # type: ignore
        return get_cached_vectorstores_for_user_profile_id(pk=user_profile.id)  # type: ignore

    def __str__(self):
        return f"{self.id}: {self.name}({self.backend}) - {self.user_profile}"  # type: ignore


__all__ = ["VectorDatabase", "VectorDatabaseBackendKind", "VectorDatabaseStatus"]
