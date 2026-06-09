"""
Module for enumerations related to vector store backends.
"""

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
        QDRANT: Represents the Qdrant vector store backend.
        WEAVIATE: Represents the Weaviate vector store backend.
        PINECONE: Represents the Pinecone vector store backend.

    Methods:
        str_to_backend(cls, backend_str: str) -> "SmarterVectorStoreBackends":
            Convert a string to a SmarterVectorStoreBackends enumeration value.
        all_backends(cls) -> list:
            Return a list of all vector store backends.
    """

    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    PINECONE = "pinecone"

    @classmethod
    def str_to_backend(cls, backend_str: str) -> "SmarterVectorStoreBackends":
        """
        Convert a string to a SmarterVectorStoreBackends enumeration value.
        """
        if isinstance(backend_str, bytes):
            backend_str = backend_str.decode("utf-8")

        # Try case-insensitive key lookup
        for _, member in cls.__members__.items():
            if member.value.lower() == backend_str.lower():
                return member

        raise SmarterValueError(f"Invalid SmarterVectorStoreBackends value: {backend_str}.")
