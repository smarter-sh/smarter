"""Smarter API Manifest - Plugin.spec"""

import logging
import os
from typing import Optional

from langchain_community.vectorstores.utils import DistanceStrategy
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
logger_prefix = formatted_text(f"{__name__}.SAMVectorstoreSpec()")


class SAMVectorstoreInterface(SmarterBasePydanticModel):
    """
    Smarter API - Vectorstore ORM Specification.

    This interface derives from a combination of
    langchain_core.vectorstores.base.VectorStoreRetriever,
    plus that which is required for establishing an authenticated connections to a
    vector database and for configuring the vectorstore manifest in the Smarter API.
    """

    text_key: Optional[str] = Field(
        None,
        description="The key in the vector database where the original text is stored, if applicable.",
        alias="textKey",
    )
    namespace: Optional[str] = Field(
        None, description="The namespace to use for the vector database, if applicable.", alias="namespace"
    )
    distance_strategy: Optional[str] = Field(
        None,
        description="The distance strategy to use for similarity search (e.g., cosine, euclidean, dot_product), if applicable.",
        alias="distanceStrategy",
    )

    @field_validator("distance_strategy")
    def validate_distance_strategy(cls, v):
        """
        Validate that the distance_strategy value is a non-empty string and matches DistanceStrategy enum if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore distance_strategy must not be empty if provided.")
            valid_values = {item.value for item in DistanceStrategy}
            if v not in valid_values:
                raise SAMValidationError(
                    f"Unsupported distance_strategy: {v}. Supported strategies are: {', '.join(valid_values)}."
                )
        return v

    @field_validator("text_key")
    def validate_text_key(cls, v):
        """
        Validate that the text_key value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore text_key must not be empty if provided.")
        return v

    @field_validator("namespace")
    def validate_namespace(cls, v):
        """
        Validate that the namespace value is a non-empty string if provided.
        """
        if v is not None:
            v = str(v).strip()
            if not v:
                raise SAMValidationError("Vectorstore namespace must not be empty if provided.")
        return v


__all__ = ["SAMVectorstoreInterface"]
