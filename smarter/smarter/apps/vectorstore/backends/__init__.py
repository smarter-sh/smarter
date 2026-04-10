# pylint: disable=import-outside-toplevel
"""
vectorstore backends.
"""

import logging
from typing import Dict, Optional, Type
from urllib.parse import urlparse

from langchain_core.embeddings.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
from smarter.apps.vectorstore.models import VectorDatabase
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

# Smarter VectorStore backends
from .base import SmarterVectorstoreBackend
from .pinecode import PineconeBackend
from .qdrant import QdrantBackend
from .weaviate import WeaviateBackend


# pylint: disable=unused-argument
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class Backends:
    """
    The Backend service pattern for the Smarter VectorStore Model.

    This class provides the mapping and logic for selecting the correct Backend
    implementation based on the manifest ``Kind``. Backends are used throughout
    the ``api/v1/cli`` interface to process Smarter YAML manifests and to
    facilitate common CLI operations, including:

        - ``create``
        - ``delete``
        - ``upsert``
        - ``query``

    Each Backend is responsible for brokering the correct implementation class
    for a given operation by analyzing the manifest's ``Kind`` field. This
    enables a unified interface for handling different resource types in the
    Smarter platform.

    Key Methods
    -----------
    get_backend(kind: str) -> Optional[Type[AbstractBackend]]:
        Returns the Backend class definition for the given manifest kind.
        The lookup is case-insensitive.

    Usage
    -----
    Backends are primarily used for processing Smarter YAML manifests in CLI
    workflows. By calling :meth:`get_backend`, you can retrieve the appropriate
    Backend class to handle a specific resource type.

    Example
    -------
    >>> broker_cls = Backends.get_backend("Account")
    >>> backend = broker_cls()
    >>> backend.describe(...)

    """

    _backends: Dict[str, Type[SmarterVectorstoreBackend]] = {
        SmarterVectorStoreBackends.QDRANT.value: QdrantBackend,
        SmarterVectorStoreBackends.WEAVIATE.value: WeaviateBackend,
        SmarterVectorStoreBackends.PINECONE.value: PineconeBackend,
    }

    @classmethod
    def get_backend(
        cls,
        name: str,
        backend: str,
        embeddings: Optional[Embeddings] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> SmarterVectorstoreBackend:
        """Case insensitive backend getter."""
        backend = backend.lower()
        if backend not in SmarterVectorStoreBackends.all():
            raise SmarterValueError(f"Unsupported backend backend: {backend}")
        BackendClass = cls._backends[backend]
        db = VectorDatabase.get_cached_object(name=name, backend=backend)
        return BackendClass(db, embeddings=embeddings, vector_store=vector_store)  # type: ignore

    @classmethod
    def snake_to_camel(cls, snake_str):
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @classmethod
    def get_backend_kind(cls, backend: str) -> Optional[str]:
        """
        Case insensitive backend backend getter. Returns the original SmarterVectorStoreBackends
        key string from cls._backends for the given backend.
        """
        if not backend:
            return None

        # remove trailing 's' from backend if it exists
        if backend.endswith("s"):
            backend = backend[:-1]

        # ensure backend is in camel case
        backend = cls.snake_to_camel(backend)
        lower_kind = backend.lower()

        # perform a lower case search to find and return the original key
        # in the cls._backends dictionary
        for key in cls._backends:
            if key.lower() == lower_kind:
                return key
        return None

    @classmethod
    def all_backends(cls) -> list[str]:
        return list(cls._backends.keys())

    @classmethod
    def from_url(cls, url) -> Optional[str]:
        """
        Returns the backend of backend from the given URL. This is used to
        determine the backend to use when the backend is not provided in the
        request.

        example: http://localhost:9357/api/v1/cli/example_manifest/account/
        returns: "Account"
        """
        parsed_url = urlparse(url)
        if parsed_url:
            slugs = parsed_url.path.split("/")
            if not "api" in slugs:
                return None
            for slug in slugs:
                this_slug = str(slug).lower()
                backend = cls.get_backend_kind(this_slug)
                if backend:
                    return backend
        logger.warning("Backends.from_url() could not extract manifest backend from URL: %s", url)


# an internal self-check to ensure that all SmarterVectorStoreBackends have a Backend implementation
if not all(item in SmarterVectorStoreBackends.all() for item in Backends.all_backends()):
    backends_keys = set(Backends.all_backends())
    backends_values = set(SmarterVectorStoreBackends.all())
    difference = backends_keys.difference(backends_values)
    difference_list = list(difference)
    if len(difference_list) == 1:
        difference_list = difference_list[0]

    raise SmarterConfigurationError(
        f"The following backend(s) is/are missing from the master BACKENDS dictionary: {difference_list}"
    )


__all__ = ["Backends", "QdrantBackend", "WeaviateBackend", "PineconeBackend"]
