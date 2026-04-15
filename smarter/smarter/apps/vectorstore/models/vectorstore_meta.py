"""
Models for the vectorstore app.
"""

import logging
from typing import Optional

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
    User,
)
from smarter.apps.connection.models import ApiConnection
from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
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


class VectorstoreBackendKind(models.TextChoices):
    """
    Enum representing the supported backend kinds for the vector database.
    """

    QDRANT = (SmarterVectorStoreBackends.QDRANT.value, SmarterVectorStoreBackends.QDRANT.value)
    WEAVIATE = (SmarterVectorStoreBackends.WEAVIATE.value, SmarterVectorStoreBackends.WEAVIATE.value)
    PINECONE = (SmarterVectorStoreBackends.PINECONE.value, SmarterVectorStoreBackends.PINECONE.value)


class VectorstoreStatus(models.TextChoices):
    """
    Enum representing the possible statuses of the vector database.
    """

    PROVISIONING = ("provisioning", "Provisioning")
    READY = ("ready", "Ready")
    FAILED = ("failed", "Failed")
    DELETING = ("deleting", "Deleting")


class VectorestoreMeta(MetaDataWithOwnershipModel):
    """
    Model representing a vector database.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Vectorstore Metadata"
        verbose_name_plural = "Vectorstore Metadata"

    objects: MetaDataWithOwnershipModelManager["VectorestoreMeta"] = MetaDataWithOwnershipModelManager()

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
        choices=VectorstoreBackendKind.choices,
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
        choices=VectorstoreStatus.choices,
        default=VectorstoreStatus.PROVISIONING,
        blank=False,
        null=False,
    )

    @classmethod
    def get_cached_object(cls, *args, backend: Optional[str] = None, **kwargs) -> "VectorestoreMeta":
        """
        Retrieve a cached VectorestoreMeta object based on the provided name and backend.
        This method is used to optimize backend retrieval by caching database objects.

        Args:
            backend (str): The backend kind of the vector database.
        Returns:
            VectorestoreMeta: The cached VectorestoreMeta object matching the name and backend.
        """

        @cache_results(cls.cache_expiration)
        def _get_object_by_name_and_backend(name: str, backend: str) -> "VectorestoreMeta":
            """
            Internal method to retrieve a model instance by primary key with caching.
            Prefetches related tags and selects related user profile, account, and
            user for optimal access. Handles most common SAM pk retrieval scenarios.

            :param name: The name of the vector database.
            :param backend: The backend kind of the vector database.

            :returns: The model instance if found, otherwise None.
            :rtype: Optional["VectorestoreMeta"]
            """
            try:
                retval = (
                    cls.objects.prefetch_related("tags")
                    .select_related("user_profile", "user_profile__account", "user_profile__user")
                    .get(name=name, backend=backend)
                )
                logger.debug(
                    "%s._get_object_by_pk() fetched %s - %s",
                    formatted_text(VectorestoreMeta.__name__ + ".get_cached_object()"),
                    type(retval).__name__,
                    str(retval),
                )
                return retval
            except cls.DoesNotExist:
                logger.debug(
                    "%s._get_object_by_name_and_backend() no %s object found for name: %s and backend: %s",
                    formatted_text(VectorestoreMeta.__name__ + ".get_cached_object()"),
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
    def get_cached_vectorstores_for_user(cls, user: User, invalidate: bool = False) -> list["VectorestoreMeta"]:
        """
        Return a list of all instances of :class:`VectorestoreMeta`.

        This method retrieves all vector store objects associated with the user's account.
        It is useful for enumerating all available vector stores for a given user.

        :param user: The user whose vector stores should be retrieved.
        :type user: User
        :return: A list of all vector store instances for the user's account.
        :rtype: list[VectorestoreMeta]

        **Example:**

        .. code-block:: python

            vectorstores = VectorestoreMeta.get_cached_vectorstores_for_user(user)
            # returns [<VectorestoreMeta ...>, <VectorestoreMeta ...>, ...]

        See also:

        - :func:`smarter.apps.account.utils.get_cached_account_for_user`
        """
        logger_prefix = formatted_text(f"{__name__}.{VectorestoreMeta.__name__}.get_cached_vectorstores_for_user()")
        logger.debug("%s called with user: %s and invalidate: %s", logger_prefix, user, invalidate)

        if user is None:
            logger.warning("%s.get_cached_vectorstores_for_user: user is None", logger_prefix)
            return []

        @cache_results()
        def get_cached_vectorstores_for_user_id(user_id: int) -> list["VectorestoreMeta"]:
            logger.debug(
                "%s.get_cached_vectorstores_for_user_id() fetching vector stores for user: %s",
                logger_prefix,
                user,
            )
            retval = VectorestoreMeta.objects.with_read_permission_for(user)
            return list(retval)

        if invalidate:
            get_cached_vectorstores_for_user_id.invalidate(user_id=user.id)  # type: ignore
        return get_cached_vectorstores_for_user_id(user_id=user.id)  # type: ignore

    def __str__(self):
        return f"{self.id}: {self.name}({self.backend}) - {self.user_profile}"  # type: ignore


__all__ = ["VectorestoreMeta", "VectorstoreBackendKind", "VectorstoreStatus"]
