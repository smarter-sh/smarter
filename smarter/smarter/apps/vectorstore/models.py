"""
Models for the vectorstore app.
"""

import logging
from typing import Optional

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    Secret,
    User,
    UserProfile,
)
from smarter.apps.account.utils import (
    SmarterCachedObjects,
    get_cached_admin_user_for_account,
)
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

    backend = models.CharField(
        help_text="The backend type for the vector database (e.g., qdrant, weaviate, pinecone).",
        max_length=50,
        choices=VectorDatabaseBackendKind.choices,
        blank=False,
        null=False,
    )

    host = models.CharField(
        help_text="The host address of the vector database.", max_length=255, blank=False, null=False
    )
    port = models.IntegerField(
        help_text="The port number for the vector database.",
        blank=False,
        null=False,
    )
    auth_config = models.JSONField(
        help_text="The authentication configuration for the vector database.", default=dict, blank=True, null=True
    )
    password = models.ForeignKey(
        Secret,
        help_text="The Smarter Secret object containing the password or API key for the vector database.",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vector_databases",
    )

    config = models.JSONField(
        help_text="The configuration settings for the vector database.", default=dict, blank=True, null=True
    )

    is_active = models.BooleanField(
        help_text="Indicates whether the vector database is active.", default=True, blank=True, null=False
    )
    status = models.CharField(
        help_text="The current status of the vector database (e.g., provisioning, ready, failed, deleting).",
        max_length=50,
        choices=VectorDatabaseStatus.choices,
        default=VectorDatabaseStatus.PROVISIONING,
        blank=False,
        null=False,
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

    def save(self, *args, **kwargs):
        """
        Override the save method to include validation for the provider model's
        embedding support.
        """

        if self.provider_model is not None and not self.provider_model.supports_embedding:
            raise SmarterValueError(
                f"The provider model {self.provider_model} does not support embedding, which is required for vector databases."
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
        return f"{self.id} - {self.name} ({self.backend}) - {self.user_profile}"  # type: ignore
