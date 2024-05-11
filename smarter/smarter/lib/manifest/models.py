"""Pydantic models for Smarter API Manifests."""

import abc
import re
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError


# from ...apps.api.v1.manifests.enum import SAMKinds
# from ...apps.api.v1.manifests.version import SMARTER_API_VERSION


class SmarterBaseModel(BaseModel):
    """Smarter API Base Pydantic Model."""

    model_config = ConfigDict(
        from_attributes=True,  # allow model to be initialized from class attributes
        arbitrary_types_allowed=True,  # allow Field attributed to be created from custom class types
        frozen=True,  # models are read-only
    )


class AbstractSAMMetadataBase(SmarterBaseModel, abc.ABC):
    """Pydantic Metadata base class. Expected to be subclassed by specific manifest classes."""

    name: str = Field(..., description="The name of the manifest resource")
    description: str = Field(..., description="The description of the manifest resource")
    version: str = Field(..., description="The version of the manifest")
    tags: Optional[List[str]] = Field(None, description="The tags of the manifest")
    annotations: Optional[List[str]] = Field(None, description="The annotations of the manifest")

    @field_validator("name")
    def validate_name(cls, v) -> str:
        if v in [None, ""]:
            raise SAMValidationError("Missing required key name")
        if len(v) > 50:
            raise SAMValidationError("Name must be less than 50 characters")
        if not re.match(SmarterValidator.VALID_CLEAN_STRING, v):
            raise SAMValidationError(
                f"Invalid name: {v}. Ensure that you do not include characters that are not URL friendly."
            )
        return v

    @field_validator("description")
    def validate_description(cls, v) -> str:
        if v in [None, ""]:
            raise SAMValidationError("Missing required key description")
        return v

    @field_validator("version")
    def validate_version(cls, v) -> str:
        if v in [None, ""]:
            raise SAMValidationError("Missing required key version")
        if not re.match(SmarterValidator.VALID_SEMANTIC_VERSION, v):
            raise SAMValidationError(
                f"Invalid semantic version. Expected semantic version (ie '1.0.0-alpha') but got {v}"
            )
        return v

    @field_validator("tags")
    def validate_tags(cls, v) -> List[str]:
        if isinstance(v, list):
            for tag in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, tag):
                    raise SAMValidationError(
                        f"Invalid tag: {tag}. Ensure that you do not include characters that are not URL friendly."
                    )
        return v

    @field_validator("annotations")
    def validate_annotations(cls, v) -> List[str]:
        if isinstance(v, list):
            for annotation in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, annotation):
                    raise SAMValidationError(
                        f"Invalid annotation: {annotation}. Ensure that you do not include characters that are not URL friendly."
                    )
        return v


class AbstractSAMSpecBase(SmarterBaseModel, abc.ABC):
    """Pydantic Spec base class. Expected to be subclassed by specific manifest classes."""


class AbstractSAMStatusBase(SmarterBaseModel, abc.ABC):
    """Pydantic Status base class. Expected to be subclassed by specific manifest classes."""


class AbstractSAMBase(SmarterBaseModel, abc.ABC):
    """
    Pydantic Smarter API Manifest ("SAM") base class. This is a base class
    for all Smarter API manifests. It provides methods for validating the
    manifest data against a strongly-typed specification, and for accessing
    the manifest data in a structured way. It is designed to be subclassed by
    specific manifest classes that implement the specific manifest data and
    methods for that manifest.
    """

    apiVersion: str = Field(
        ...,
        description="apiVersion[String]: Required. The API version of the AbstractSAMBase.",
    )
    kind: str = Field(
        ...,
        description="kind[String]: Required. The kind of resource described by the manifest.",
    )
    metadata: Union[AbstractSAMMetadataBase, dict] = Field(
        ..., description="metadata[obj]: Required. The manifest metadata."
    )
    spec: AbstractSAMSpecBase = Field(..., description="spec[obj]: Required. The manifest specification.")
    status: Optional[AbstractSAMStatusBase] = Field(
        None,
        description="status[obj]: Optional. Read-only. The run-time state of the resource described by the manifest.",
    )

    # @field_validator("apiVersion")
    # def validate_apiVersion(cls, v) -> str:
    #     """Validate apiVersion"""
    #     if v in [None, ""]:
    #         raise SAMValidationError("Missing required manifest key: apiVersion")
    #     if v != SMARTER_API_VERSION:
    #         raise SAMValidationError(f"Invalid apiVersion. Expected {SMARTER_API_VERSION} but got {v}")
    #     return v

    # @field_validator("kind")
    # def validate_kind(cls, v) -> str:
    #     """Validate kind"""
    #     if v in [None, ""]:
    #         raise SAMValidationError("Missing required manifest key: kind")
    #     if v not in SAMKinds.all_values():
    #         raise SAMValidationError(f"Invalid kind. Must be one of {SAMKinds.all_values()} but got {v}")
    #     return v

    @field_validator("metadata")
    def validate_metadata(cls, v) -> AbstractSAMMetadataBase:
        """Validate metadata"""
        if isinstance(v, dict):
            return AbstractSAMMetadataBase(**v)
        return v
