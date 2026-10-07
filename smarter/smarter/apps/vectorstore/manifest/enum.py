"""Smarter API Vectorstore Manifest - enumerated datatypes."""

from smarter.common.enum import SmarterEnumAbstract


class SAMVectorstoreSpecKeys(SmarterEnumAbstract):
    """The keys of a Vectorstore manifest's spec."""

    BACKEND = "backend"
    HOSTING = "hosting"
    CONNECTION = "connection"
    IS_ACTIVE = "isActive"
    INDEX = "index"
    EMBEDDINGS = "embeddings"
    SELF_HOSTED = "selfHosted"
    PINECONE = "pinecone"
    MAINTENANCE = "maintenance"


__all__ = ["SAMVectorstoreSpecKeys"]
