"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field, field_validator

from smarter.apps.vectorstore.enum import SmarterVectorStoreBackends
from smarter.lib.django import waffle
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase, SmarterBasePydanticModel

from .const import MANIFEST_KIND


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMVectorstoreORMSpec(SmarterBasePydanticModel):
    """Smarter API - Vectorstore ORM Specification."""

    name: str = Field(
        ...,
        description="The name of the Vectorstore. Case sensitive. Must be unique and not empty, with no leading or trailing whitespace and no special characters. examples: 'OpenAI', 'GoogleAI', 'MetaAI'.",
    )
    description: Optional[str] = Field(
        None,
        description="A brief description of the Vectorstore.",
    )
    backend: str = Field(
        ..., description="The backend type for the vector database (e.g., qdrant, weaviate, pinecone)."
    )
    host: str = Field(..., description="The host address of the vector database.")
    port: int = Field(..., description="The port number for the vector database.")
    auth_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="The authentication configuration for the vector database."
    )
    password: Optional[str] = Field(
        None,
        description=(
            "The name of a Smarter Secret object containing the "
            "password or API key for the vector database and owned by the "
            "authenticated API user."
        ),
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="The configuration settings for the vector database."
    )
    is_active: bool = Field(default=True, description="Indicates whether the vector database is active.")
    provider: str = Field(
        ...,
        description="The name of a Smarter provider associated with this vector database and owned by the authenticated API user.",
    )
    provider_model: Optional[str] = Field(
        None, description="The name of a Smarter provider model related to the Smarter Provider."
    )

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

    @field_validator("host")
    def validate_host(cls, v):
        """
        Validate that the host value is not empty and is a valid hostname or IP address.
        """
        v = str(v).strip()
        if not v:
            raise SAMValidationError("Vectorstore host must not be empty.")
        if not SmarterValidator.is_valid_hostname(v):
            raise SAMValidationError(f"Invalid vectorstore host: {v}. Must be a valid hostname or IP address.")
        return v

    @field_validator("port")
    def validate_port(cls, v):
        """
        Validate that the port value is a valid integer between 1 and 65535."""
        if not SmarterValidator.is_valid_port(v):
            raise SAMValidationError(f"Invalid vectorstore port: {v}. Must be an integer between 1 and 65535.")
        return v

    @field_validator("auth_config")
    def validate_auth_config(cls, v):
        """
        Validate that the auth_config value is a dictionary if provided.
        """
        if v is not None and not isinstance(v, dict):
            raise SAMValidationError("Vectorstore auth_config must be a dictionary.")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        """
        Validate that the password value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore password must not be empty if provided.")
        return v

    @field_validator("config")
    def validate_config(cls, v):
        """
        Validate that the config value is a dictionary if provided.
        """
        if v is not None and not isinstance(v, dict):
            raise SAMValidationError("Vectorstore config must be a dictionary.")
        return v

    @field_validator("is_active")
    def validate_is_active(cls, v):
        """
        Validate that the is_active value is a boolean.
        """
        if not isinstance(v, bool):
            raise SAMValidationError("Vectorstore is_active must be a boolean value.")
        return v

    @field_validator("provider")
    def validate_provider(cls, v):
        """
        Validate that the provider value is a non-empty string if provided.
        """
        v = str(v).strip()
        if not v:
            raise SAMValidationError("Vectorstore provider must not be empty.")
        return v

    @field_validator("provider_model")
    def validate_provider_model(cls, v):
        """
        Validate that the provider_model value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore provider_model must not be empty if provided.")
        return v


class SAMVectorstoreSpec(AbstractSAMSpecBase):
    """Smarter API Vectorstore Manifest Vectorstore.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    vectorstore: SAMVectorstoreORMSpec = Field(
        ..., description=f"{class_identifier}.selector[obj]: the spec for the {MANIFEST_KIND}"
    )
