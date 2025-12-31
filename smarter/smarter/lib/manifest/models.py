"""Pydantic models for Smarter API Manifests."""

import abc
import datetime
import decimal
import re
import uuid
from logging import getLogger
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.utils import camel_to_snake
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError


logger = getLogger(__name__)

VALID_ANNOTATION_VALUE_TYPES_SET = (
    str,
    int,
    float,
    bool,
    datetime.date,
    datetime.datetime,
    decimal.Decimal,
    uuid.UUID,
    bytes,
    list,
    dict,
)
"""
Types allowed for annotation values in manifest metadata.
"""
AnnotationValueType = Union[
    str, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict
]


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
    """
    Abstract base class for manifest metadata in the Smarter API.

    This class defines the required structure and validation logic for metadata associated with
    Smarter API manifests. It is designed to be subclassed by concrete manifest metadata classes,
    which may extend or customize the metadata fields as needed for specific resource types.

    The ``AbstractSAMMetadataBase`` enforces strong typing and validation for core metadata fields,
    such as resource name, description, version, tags, and annotations. It ensures that all metadata
    adheres to expected formats and constraints, promoting consistency and reliability across all
    manifest definitions.

    Subclasses should inherit from this class to implement metadata for their specific manifest
    types. This approach encourages code reuse, enforces validation, and provides a unified
    interface for working with manifest metadata throughout the Smarter API ecosystem.

    .. note::

        This class is abstract and should not be instantiated directly. Instead, create subclasses
        that define any additional fields or validation required for your manifest's metadata.
    """

    name: str = Field(..., description="The camelCase name of the manifest resource")
    description: str = Field(
        ..., description="The description for this resource. Be brief. Keep it under 255 characters."
    )
    version: str = Field(..., description="The semantic version of the manifest. Example: 0.1.0")
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="The tags of the manifest. Used for generic resource categorization and search. Example: ['tag1', 'tag2']",
    )
    annotations: Optional[List[dict[str, AnnotationValueType]]] = Field(
        default_factory=list,
        description="""The manifest annotations. Used for storing arbitrary metadata as
            key-value pairs. Example: [{'smarter.sh/test-manifest/project-name': 'Scooby dooby do'}]. The
            key should be a valid url-friendly string. The value accepts
            multi-line string values (YAML block scalars) and various scalar types including
            str, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict.
            """,
    )

    @field_validator("name")
    def validate_name(cls, v) -> str:
        """
        Validates the ``name`` field for a manifest.

        Ensures the value is a string, present, and meets all constraints. Raises if not a string.
        """
        if not isinstance(v, str):
            raise SAMValidationError(f"Manifest 'name' must be a string, got {type(v)}.")
        v = v.strip()
        if v == "":
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
        # Final guarantee: always return a string
        if not isinstance(v, str):
            raise SAMValidationError(f"Manifest 'name' must be a string after processing, got {type(v)}.")
        return v

    @field_validator("description")
    def validate_description(cls, v) -> str:
        """
        Validates the ``description`` field for a manifest.
        This method ensures that the ``description`` attribute is present. If the value is missing,
        a ``SAMValidationError`` is raised.

        :param v: The value of the ``description`` field to validate.
        :type v: str
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If the value is missing.
        :return: The validated ``description`` string.
        :rtype: str
        """
        if v in [None, ""]:
            raise SAMValidationError("Missing required key description")
        return v

    @field_validator("version")
    def validate_version(cls, v) -> str:
        """
        Validates the ``version`` field for a manifest.
        This method ensures that the ``version`` attribute is present and follows semantic versioning
        rules. If the value is missing or invalid, a ``SAMValidationError`` is raised

        :param v: The value of the ``version`` field to validate.
        :type v: str
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If the value is missing or invalid.
        :return: The validated ``version`` string.
        :rtype: str
        """
        if v in [None, ""]:
            raise SAMValidationError("Missing required key version")
        if not re.match(SmarterValidator.VALID_SEMANTIC_VERSION, v):
            raise SAMValidationError(
                f"Invalid semantic version. Expected semantic version (ie '1.0.0-alpha') but got {v}"
            )
        return v

    @field_validator("tags")
    def validate_tags(cls, v) -> Optional[List[str]]:
        """
        Validates the ``tags`` field for a manifest.
        This method ensures that each tag in the ``tags`` list adheres to URL-friendly character
        rules. If any tag is invalid, a ``SAMValidationError`` is raised.

        :param v: The value of the ``tags`` field to validate.
        :type v: Optional[List[str]]
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If any tag is invalid.
        :return: The validated list of tags.
        :rtype: Optional[List[str]]
        """
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
    def validate_annotations(cls, v) -> Optional[List[dict[str, AnnotationValueType]]]:
        """
        Validates the ``annotations`` field for a manifest.
        Accepts a list of dicts, where each dict can be a single key-value pair or a flat dict with multiple key-value pairs.
        Supports multi-line string values (YAML block scalars).
        Ensures each annotation key is URL-friendly and each value is a string or scalar (including multi-line strings).
        Raises SAMValidationError if invalid.

        :param v: The value of the ``annotations`` field to validate.
        :type v: Optional[List[dict[str, Any]]]
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If any annotation is invalid.
        :return: The validated list of annotations.
        :rtype: Optional[List[dict[str, Any]]]
        """
        if v is None:
            return v
        if not isinstance(v, list):
            raise SAMValidationError("Annotations must be a list of dictionaries.")
        for annotation in v:
            if not isinstance(annotation, dict):
                raise SAMValidationError(f"Each annotation must be a dictionary, got {type(annotation)}: {annotation}")
            for key, value in annotation.items():
                # Key must be URL-friendly
                if not re.match(SmarterValidator.VALID_URL_FRIENDLY_STRING, str(key)):
                    raise SAMValidationError(
                        f"Invalid annotation key: {key}. Ensure that you do not include characters that are not URL friendly."
                    )
                # Accept string, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict, or None as value
                allowed_types = VALID_ANNOTATION_VALUE_TYPES_SET
                if not isinstance(value, allowed_types) and value is not None:
                    raise SAMValidationError(
                        f"Invalid annotation value type for key '{key}': {type(value)}. Must be a string, int, float, bool, date, datetime, Decimal, UUID, bytes, list, dict, or None."
                    )
                # If string, allow multi-line (YAML block scalar) and comma-separated values
                if isinstance(value, str):
                    # Allow any string, but optionally check for length or forbidden characters
                    if len(value) > 2048:
                        raise SAMValidationError(f"Annotation value for key '{key}' is too long (max 2048 chars).")
        return v


class AbstractSAMSpecBase(SmarterBasePydanticModel, abc.ABC):
    """Pydantic Spec base class. Expected to be subclassed by specific manifest classes."""


class AbstractSAMStatusBase(SmarterBasePydanticModel, abc.ABC):
    """Pydantic Status base class. Expected to be subclassed by specific manifest classes."""


class AbstractSAMBase(SmarterBasePydanticModel, abc.ABC):
    """
    Abstract base class for all Smarter API Manifest (SAM) models.

    This class serves as the foundational Pydantic model for representing Smarter API manifests.
    It is intended to be subclassed by concrete manifest classes that define specific resource types
    within the Smarter API ecosystem.

    The ``AbstractSAMBase`` class provides a strongly-typed structure for manifest data, ensuring
    that all manifests adhere to a consistent schema and validation logic. It includes built-in
    validation for core manifest fields and supports structured access to manifest data.

    Subclasses should implement or extend this class to define the specific data and behaviors
    required for their respective manifest types. This design promotes code reuse, type safety,
    and robust validation across all Smarter API manifests.

    The class also provides methods for validating manifest data and for representing the manifest
    as a string for debugging or logging purposes.

    .. note::

        Do not instantiate this class directly. Instead, create subclasses that define the
        required fields and any additional validation or methods specific to your manifest type.

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
        """
        Validates the ``apiVersion`` field for a manifest.

        This method ensures that the ``apiVersion`` attribute is present and matches one of the
        supported API versions defined in ``SmarterApiVersions``. If the value is missing or invalid,
        a ``SAMValidationError`` is raised.

        :param v: The value of the ``apiVersion`` field to validate.
        :type v: str
        :raises smarter.lib.manifest.exceptions.SAMValidationError: If the value is missing or not a supported version.
        :return: The validated ``apiVersion`` string.
        :rtype: str
        """
        if v in [None, ""]:
            raise SAMValidationError("Missing required manifest key: apiVersion")
        if v not in SmarterApiVersions.all_values():
            raise SAMValidationError(f"Invalid version. Must be one of {SmarterApiVersions.all_values()} but got {v}")
        return v

    @field_validator("metadata")
    def validate_metadata(cls, v) -> AbstractSAMMetadataBase:
        """
        Validates the ``metadata`` field for a manifest.

        This method ensures that the ``metadata`` attribute is an instance of
        :class:`AbstractSAMMetadataBase`. If a dictionary is provided, it will be coerced
        into an ``AbstractSAMMetadataBase`` object. This guarantees that the manifest metadata
        is always properly structured and validated.

        :param v: The value of the ``metadata`` field to validate.
        :type v: dict or AbstractSAMMetadataBase
        :return: The validated ``metadata`` object.
        :rtype: AbstractSAMMetadataBase
        """
        if isinstance(v, dict):
            return AbstractSAMMetadataBase(**v)
        return v

    def __str__(self) -> str:
        return f"{self.formatted_class_name}(apiVersion={self.apiVersion}, kind={self.kind})"
