"""
The storage service: the platform's private object storage, for files that only their owner may download.

The environment's public bucket serves the web console and the chat widget through the CDN, so
everything in it is public. Files that belong to one person, e.g. the archive of a user's data
export, go to private storage instead, and are shared with a link that expires: a presigned url.

The platform uses :class:`StorageService` through
:data:`smarter.apps.infrastructure.services.infrastructure` ``.storage``, and the cloud provider
implements it, e.g. :class:`~smarter.apps.infrastructure.providers.aws.storage.S3StorageService`
with the environment's private exports bucket, ``smarter_settings.aws_s3_exports_bucket_name``.

.. code-block:: python

    from smarter.apps.infrastructure.services import infrastructure

    infrastructure.storage.put_object("data-exports/42/export.zip", content, "application/zip")
    url = infrastructure.storage.presigned_url("data-exports/42/export.zip", expires_in=86400, filename="export.zip")
    infrastructure.storage.delete_object("data-exports/42/export.zip")
"""

from abc import abstractmethod
from typing import Optional

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..const import InfrastructureServiceNames
from ..exceptions import StorageServiceError
from .base import InfrastructureService

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

MAX_PRESIGNED_URL_SECONDS = 7 * 24 * 60 * 60
"""The longest that a presigned url may last: seven days, the most that AWS S3 allows."""


class StorageService(InfrastructureService):
    """
    The private object storage of a cloud provider.

    Objects are private: nobody can read one without the provider's credentials, or a presigned
    url, which :meth:`presigned_url` makes.

    :param provider_name: The name of the provider, e.g. ``aws``.
    """

    service_name = InfrastructureServiceNames.STORAGE
    error_class = StorageServiceError

    # --------------------------------------------------------------------------
    # primitives, which a provider implements
    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def bucket(self) -> str:
        """The name of the private bucket, or its equivalent, that holds the objects."""

    @abstractmethod
    def _put_object(self, key: str, content: bytes, content_type: str) -> None:
        """Save an object, replacing any object of the same key."""

    @abstractmethod
    def _presigned_url(self, key: str, expires_in: int, filename: Optional[str]) -> str:
        """Return a url that downloads an object until it expires, as an attachment named ``filename``."""

    @abstractmethod
    def _delete_object(self, key: str) -> None:
        """Delete an object.

        Deleting an object that does not exist is not an error.
        """

    # --------------------------------------------------------------------------
    # operations
    # --------------------------------------------------------------------------
    def put_object(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> None:
        """
        Save a private object.

        :param key: The object's key, e.g. ``data-exports/42/export.zip``.
        :param content: The object's contents.
        :param content_type: The object's MIME type, e.g. ``application/zip``.
        :raises InfrastructureNotReadyError: If the service is not ready.
        :raises StorageServiceError: If the object cannot be saved.
        """
        self.require_ready()
        with self.operation("put_object"):
            self._put_object(key, content, content_type)
        logger.info(
            "%s.put_object() saved %s (%s bytes) to %s", self.formatted_class_name, key, len(content), self.bucket
        )

    def presigned_url(self, key: str, expires_in: int, filename: Optional[str] = None) -> str:
        """
        Return a url that downloads a private object, without credentials, until it expires.

        Anyone who has the url can download the object until then, so it is sent only to the
        object's owner.

        :param key: The object's key.
        :param expires_in: How many seconds the url works, at most seven days.
        :param filename: The file name that the browser saves the download as, or None for the key's.
        :returns: The url.
        :raises StorageServiceError: If ``expires_in`` is out of range, or the url cannot be made.
        """
        if expires_in < 1 or expires_in > MAX_PRESIGNED_URL_SECONDS:
            raise StorageServiceError(
                f"A presigned url lasts between 1 and {MAX_PRESIGNED_URL_SECONDS} seconds, not {expires_in}."
            )
        self.require_ready()
        with self.operation("presigned_url"):
            url = self._presigned_url(key, expires_in, filename)
        logger.info(
            "%s.presigned_url() made a url for %s that expires in %s seconds",
            self.formatted_class_name,
            key,
            expires_in,
        )
        return url

    def delete_object(self, key: str) -> None:
        """
        Delete a private object, if it exists.

        :param key: The object's key.
        :raises StorageServiceError: If the object cannot be deleted.
        """
        self.require_ready()
        with self.operation("delete_object"):
            self._delete_object(key)
        logger.info("%s.delete_object() deleted %s from %s", self.formatted_class_name, key, self.bucket)


__all__ = ["MAX_PRESIGNED_URL_SECONDS", "StorageService"]
