"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, Optional, cast

from pydantic import Field, field_validator, model_validator

from smarter.apps.account.models import SmarterQuerySetWithPermissions
from smarter.apps.connection.models import ApiConnection
from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase

from ..const import MANIFEST_KIND
from .embeddings_interface import SAMEmbeddingsInterface
from .index_model_interface import SAMIndexModelInterface
from .vectorstore_interface import SAMVectorstoreInterface

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMVectorstoreSpec(AbstractSAMSpecBase):
    """Smarter API Vectorstore Manifest Vectorstore.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    connection: Optional[str] = Field(
        ...,
        description="The name of an existing Smarter APIConnection object that can be used to establish a connection to the vector database. If provided, the connection will be used instead of the host, port, auth_config, and password fields to establish the connection. The Connection object must be owned by the authenticated API user and must contain the necessary information to connect to the vector database.",
        alias="connection",
    )
    backend: str = Field(
        ..., description="The backend type for the vector database (e.g., qdrant, weaviate, pinecone).", alias="backend"
    )
    is_active: bool = Field(
        default=True, description="Indicates whether the vector database is active.", alias="isActive"
    )
    vectorstore: SAMVectorstoreInterface = Field(
        ..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND} vectorstore interface"
    )
    embeddings: SAMEmbeddingsInterface = Field(
        ..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND} embeddings interface"
    )
    indexModel: SAMIndexModelInterface = Field(
        ..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND} index model configuration"
    )

    @model_validator(mode="after")
    def validate_connection(self):
        """
        Validate that the connection value is a non-empty string if provided.
        """
        v = self.connection
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore connection must not be empty if provided.")
            api_connections = (
                ApiConnection.objects.with_read_permission_for(user=self.user)
                if self.user
                else ApiConnection.objects.filter(name=v).filter(name=v)
            )
            if not api_connections.exists():
                raise SAMValidationError(f"Vectorstore connection '{v}' does not exist.")
        return self

    @field_validator("backend")
    def validate_backend(cls, v):
        """
        Validate that the backend value is not empty and is one of the
        supported vectorstore backends.
        """
        v = str(v).strip()
        if not v:
            raise SAMValidationError("Vectorstore backend must not be empty.")
        if v not in SmarterVectorStoreBackends.all():
            raise SAMValidationError(
                f"Unsupported vectorstore backend: {v}. Supported backends are: {', '.join(SmarterVectorStoreBackends.all())}."
            )
        return v

    @field_validator("is_active")
    def validate_is_active(cls, v):
        """
        Validate that the is_active value is a boolean.
        """
        if not isinstance(v, bool):
            raise SAMValidationError("Vectorstore is_active must be a boolean value.")
        return v


__all__ = ["SAMVectorstoreSpec"]
