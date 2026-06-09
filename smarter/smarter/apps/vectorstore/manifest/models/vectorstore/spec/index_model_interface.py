"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Any, Optional

from pinecone.db_control.enums import DeletionProtection, Metric, VectorType
from pinecone.db_control.models import ByocSpec, PodSpec, ServerlessSpec
from pydantic import Field, field_validator

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from ..const import MANIFEST_KIND


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
logger_prefix = formatted_text(f"{__name__}.SAMIndexModelInterface()")


class SAMIndexModelInterface(SmarterBasePydanticModel):
    """
    Interface for index model configuration, inspired by LangChain IndexModel.

    original interface comes from pinecone.db_control.models.IndexModel
    """

    spec: Optional[dict[str, Any]] = Field(
        None,
        description="Index deployment spec. Accepts a dict, ServerlessSpec, PodSpec, or ByocSpec. Example: ServerlessSpec(cloud=CloudProvider.AWS, region=AwsRegion.US_EAST_1)",
        alias="spec",
    )
    dimension: Optional[int] = Field(
        None,
        description="Number of dimensions for the index. Must be between 1 and 20,000, or None. Example: 1536.",
        alias="dimension",
        ge=1,
        le=20000,
    )
    metric: Optional[str] = Field(
        "cosine",
        description="Distance metric for similarity search. Accepts Metric enum or string. Default: 'cosine'.",
        alias="metric",
    )
    timeout: Optional[int] = Field(
        None,
        description="Timeout in seconds for index operations. Must be greater than zero or None.",
        alias="timeout",
        gt=0,
    )
    deletion_protection: Optional[str] = Field(
        "disabled",
        description="Deletion protection setting. Accepts DeletionProtection enum or string. Default: 'disabled'.",
        alias="deletionProtection",
    )
    vector_type: Optional[str] = Field(
        "dense", description="Type of vector. Accepts VectorType enum or string. Default: 'dense'.", alias="vectorType"
    )

    @field_validator("spec")
    def validate_spec(cls, v):
        """
        Validate that the spec value is either a dict, ServerlessSpec, PodSpec, or ByocSpec if provided.

        spec: Dict[Unknown, Unknown] | ServerlessSpec | PodSpec | ByocSpec, <---- ServerlessSpec(cloud=CloudProvider.AWS, region=AwsRegion.US_EAST_1)

        from pinecone.db_control.models import ServerlessSpec
        from pinecone.db_control.enums import CloudProvider, AwsRegion

        """
        if v is not None:
            if not isinstance(v, dict):
                raise SAMValidationError(
                    "IndexModel spec must be a dictionary, or Pinecone ServerlessSpec, PodSpec, or ByocSpec."
                )
            # ensure that the value is a dict, ServerlessSpec, PodSpec, or ByocSpec
            try:
                ServerlessSpec(**v)
                logger.debug("%s IndexModel spec validated as ServerlessSpec.", logger_prefix)
            # pylint: disable=broad-except
            except Exception:
                try:
                    PodSpec(**v)
                    logger.debug("%s IndexModel spec validated as PodSpec.", logger_prefix)
                # pylint: disable=broad-except
                except Exception:
                    try:
                        ByocSpec(**v)
                        logger.debug("%s IndexModel spec validated as ByocSpec.", logger_prefix)
                    # pylint: disable=broad-except
                    except Exception as e:
                        raise SAMValidationError(
                            "IndexModel spec must be a dict that conforms to Pinecone ServerlessSpec, PodSpec, or ByocSpec."
                        ) from e
        return v

    @field_validator("metric")
    def validate_metric(cls, v):
        """
        Validate that the metric value is a valid Metric enum value or string.
        """
        valid_metrics = {item.value.lower() for item in Metric}
        if v.lower() not in valid_metrics:
            raise SAMValidationError(f"Invalid metric: {v}. Supported metrics are: {', '.join(valid_metrics)}.")
        return v.lower()

    @field_validator("deletion_protection")
    def validate_deletion_protection(cls, v):
        """
        Validate that the deletion_protection value is a valid DeletionProtection enum value or string.
        """
        valid_options = {item.value.lower() for item in DeletionProtection}
        if v.lower() not in valid_options:
            raise SAMValidationError(
                f"Invalid deletion_protection: {v}. Supported options are: {', '.join(valid_options)}."
            )
        return v.lower()

    @field_validator("vector_type")
    def validate_vector_type(cls, v):
        """
        Validate that the vector_type value is a valid VectorType enum value or string.
        """
        valid_types = {item.value.lower() for item in VectorType}
        if v.lower() not in valid_types:
            raise SAMValidationError(f"Invalid vector_type: {v}. Supported types are: {', '.join(valid_types)}.")
        return v.lower()


__all__ = ["SAMIndexModelInterface"]
