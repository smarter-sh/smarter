"""Pydantic models for Smarter API Manifests."""

import abc
import re
from logging import getLogger
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.utils import camel_to_snake
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError


logger = getLogger(__name__)


class SmarterBasePydanticModel(BaseModel, SmarterHelperMixin):
    """Smarter API Base Pydantic Model."""

    model_config = ConfigDict(
        from_attributes=True,  # allow model to be initialized from class attributes
        arbitrary_types_allowed=True,  # allow Field attributed to be created from custom class types
        frozen=True,  # models are read-only
    )

    @model_validator(mode="before")
    def coerce_none_strings(cls, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if v in ("None", ""):
                    data[k] = None
        return data


class AbstractSAMMetadataBase(SmarterBasePydanticModel, abc.ABC):
    """Pydantic Metadata base class. Expected to be subclassed by specific manifest classes."""

    name: str = Field(..., description="The camelCase name of the manifest resource")
    description: str = Field(
        ..., description="The description for this resource. Be brief. Keep it under 255 characters."
    )
    version: str = Field(..., description="The semantic version of the manifest. Example: 0.1.0")
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="The tags of the manifest. These are fully functional but are not currently used. Example: ['tag1', 'tag2']",
    )
    annotations: Optional[List[str]] = Field(
        default_factory=list,
        description="The manifest annotations. These are fully functional but are not currently used.",
    )

    @field_validator("name")
    def validate_name(cls, v) -> str:
        if v in [None, ""]:
            raise SAMValidationError("Missing required key name")
        if len(v) > 50:
            raise SAMValidationError("Name must be less than 50 characters")
        if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, v):
            raise SAMValidationError(
                f"Invalid name: {v}. Ensure that you do not include characters that are not URL friendly."
            )
        if not SmarterValidator.is_valid_snake_case(v):
            snake_case_name = camel_to_snake(v)
            logger.warning(
                "%s.name '%s' is not in snake_case. Converting to snake_case: %s. Please use snake_case for names.",
                cls.__name__,
                v,
                snake_case_name,
            )
            v = snake_case_name
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
    def validate_tags(cls, v) -> Optional[List[str]]:
        if v is None:
            return v
        if isinstance(v, list):
            for tag in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, tag):
                    raise SAMValidationError(
                        f"Invalid tag: {tag}. Ensure that you do not include characters that are not URL friendly."
                    )
        return v

    @field_validator("annotations")
    def validate_annotations(cls, v) -> Optional[List[str]]:
        if v is None:
            return v
        if isinstance(v, list):
            for annotation in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, annotation):
                    raise SAMValidationError(
                        f"Invalid annotation: {annotation}. Ensure that you do not include characters that are not URL friendly."
                    )
        return v


class AbstractSAMSpecBase(SmarterBasePydanticModel, abc.ABC):
    """Pydantic Spec base class. Expected to be subclassed by specific manifest classes."""


class AbstractSAMStatusBase(SmarterBasePydanticModel, abc.ABC):
    """Pydantic Status base class. Expected to be subclassed by specific manifest classes."""


class AbstractSAMBase(SmarterBasePydanticModel, abc.ABC):
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
    metadata: AbstractSAMMetadataBase = Field(..., description="metadata[obj]: Required. The manifest metadata.")
    spec: AbstractSAMSpecBase = Field(..., description="spec[obj]: Required. The manifest specification.")
    status: Optional[AbstractSAMStatusBase] = Field(
        default=None,
        description="status[obj]: Optional. Read-only. The run-time state of the resource described by the manifest.",
        exclude=True,
    )

    @field_validator("apiVersion")
    def validate_apiVersion(cls, v) -> str:
        """Validate apiVersion"""
        if v in [None, ""]:
            raise SAMValidationError("Missing required manifest key: apiVersion")
        if v not in SmarterApiVersions.all_values():
            raise SAMValidationError(f"Invalid version. Must be one of {SmarterApiVersions.all_values()} but got {v}")
        return v

    @field_validator("metadata")
    def validate_metadata(cls, v) -> AbstractSAMMetadataBase:
        """Validate metadata"""
        if isinstance(v, dict):
            return AbstractSAMMetadataBase(**v)
        return v

    def __str__(self) -> str:
        return f"{self.formatted_class_name}(apiVersion={self.apiVersion}, kind={self.kind})"
