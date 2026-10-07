"""Module for enumerations related to vector store backends."""

from smarter.common.enum import SmarterEnumAbstract
from smarter.common.exceptions import SmarterValueError


class SmarterVectorStoreBackends(SmarterEnumAbstract):
    """
    Enumeration of supported vector store backends.

    This class descends from :class:`SmarterEnumAbstract`, typically
    implemented as a subclassed Singleton. For flexibility, it also
    allows instantiation with a string value, enabling
    a ``SmarterVectorStoreBackends`` value to be passed as a strongly
    typed object.

    Attributes:
        QDRANT: `Qdrant <https://qdrant.tech/>`__, self-hosted on Kubernetes, or Qdrant Cloud.
        PINECONE: `Pinecone <https://www.pinecone.io/>`__, a managed service.
    """

    QDRANT = "qdrant"
    PINECONE = "pinecone"

    @classmethod
    def str_to_backend(cls, backend_str: str) -> "SmarterVectorStoreBackends":
        """Convert a string to a SmarterVectorStoreBackends enumeration value."""
        if isinstance(backend_str, bytes):
            backend_str = backend_str.decode("utf-8")

        # Try case-insensitive key lookup
        for _, member in cls.__members__.items():
            if member.value.lower() == backend_str.lower():
                return member

        raise SmarterValueError(f"Invalid SmarterVectorStoreBackends value: {backend_str}.")


class VectorstoreHosting(SmarterEnumAbstract):
    """
    Who runs a vector database.

    - ``self_hosted``: Smarter runs it on its Kubernetes cluster. Qdrant only.
    - ``managed``: a service, e.g. Pinecone or Qdrant Cloud, reached through an ApiConnection.
    """

    SELF_HOSTED = "self_hosted"
    MANAGED = "managed"


class VectorstoreMetric(SmarterEnumAbstract):
    """The distance metric of similarity search."""

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOTPRODUCT = "dotproduct"


__all__ = ["SmarterVectorStoreBackends", "VectorstoreHosting", "VectorstoreMetric"]
