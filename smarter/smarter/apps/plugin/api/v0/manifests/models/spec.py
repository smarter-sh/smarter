"""Smarter API V0 Plugin Manifest model spec."""

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import HttpRequest, SAMSpecBase, SqlConnection

# Plugin
from smarter.apps.plugin.api.v0.manifests.enum import (
    SAMPluginSpecSelectorKeyDirectiveValues,
)
from smarter.common.const import VALID_CHAT_COMPLETION_MODELS
from smarter.lib.django.validators import SmarterValidator


###############################################################################
# Plugin spec
###############################################################################


class SAMPluginSpecSelector(BaseModel):
    """Smarter API V0 Plugin Manifest - Spec - Selector class."""

    directive: str = Field(
        ...,
        description=f"Plugin.spec.selector.directive: the kind of selector directive to use for the Plugin. Must be one of: {SAMPluginSpecSelectorKeyDirectiveValues.all_values()}",
    )
    search_terms: Optional[List[str]] = Field(
        None,
        description="Plugin.spec.selector.searchTerms. The keyword search terms to use when the Plugin directive is 'searchTerms'. Keywords are most effective when constrained to 1 or 2 words each and lists are limited to a few dozen items.",
    )

    @field_validator("directive")
    def validate_directive(cls, v) -> str:
        if v not in SAMPluginSpecSelectorKeyDirectiveValues.all_values():
            raise SAMValidationError(
                f"Invalid value found in Plugin.spec.selector.directive: {v}. Must be one of {SAMPluginSpecSelectorKeyDirectiveValues.all_values()}. These values are case-sensitive and camelCase."
            )
        return v

    @field_validator("search_terms")
    def validate_search_terms(cls, v) -> List[str]:
        if isinstance(v, list):
            for search_term in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING, search_term):
                    raise SAMValidationError(
                        f"Invalid value found in Plugin.spec.selector.searchTerms: {search_term}. Avoid using characters that are not URL friendly, like spaces and special ascii characters."
                    )
        return v

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPluginSpecSelector":

        # 1. searchTerms is required when directive is 'searchTerms'
        if self.directive == SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS and self.search_terms is None:
            raise SAMValidationError(
                "Plugin.spec.selector.searchTerms is required when Plugin.spec.selector.directive is 'searchTerms'"
            )

        # 2. searchTerms is not allowed when directive is 'always'
        if self.directive != SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS and self.search_terms is not None:
            raise SAMValidationError(
                "Plugin.spec.selector.searchTerms is only used when Plugin.spec.selector.directive is 'always'"
            )

        return self


class SAMPluginSpecPrompt(BaseModel):
    """Smarter API V0 Plugin Manifest - Spec - Prompt class."""

    systemrole: str = Field(
        ...,
        description="The systemrole of the Plugin. Be verbose and specific. Ensure that the systemRole accurately conveys to the LLM how you want it to use the Plugin data that is returned.",
    )
    model: str = Field(..., description=f"The model of the Plugin. Must be one of: {VALID_CHAT_COMPLETION_MODELS}")
    temperature: float = Field(..., gt=0, lt=1.0, description="The temperature of the Plugin")
    maxtokens: int = Field(..., gt=0, description="The maxtokens of the Plugin")

    @field_validator("systemrole")
    def validate_systemrole(cls, v) -> str:
        if re.match(SmarterValidator.VALID_CLEAN_STRING, v):
            return v
        raise SAMValidationError(f"Invalid characters found in Plugin.spec.prompt.systemRole: {v}")

    @field_validator("model")
    def validate_model(cls, v) -> str:
        if v in VALID_CHAT_COMPLETION_MODELS:
            return v
        raise SAMValidationError(
            f"Invalid value found in Plugin.spec.prompt.model: {v}. Must be one of {VALID_CHAT_COMPLETION_MODELS}"
        )


class SAMPluginSpecDataSql(BaseModel):
    """Smarter API V0 Plugin Manifest Plugin.spec.data.sqlData"""

    connection: SqlConnection = Field(..., description="Plugin.spec.data.sqlData: an sql server connection")
    query: str = Field(..., description="Plugin.spec.data.sqlData: a valid SQL query")


class SAMPluginSpecData(BaseModel):
    """Smarter API V0 Plugin Manifest Plugin.spec.data"""

    description: str = Field(
        ...,
        description="Plugin.spec.data.description: A narrative description of the Plugin features that is provided to the LLM as part of a tool_chain dict",
    )
    static_data: Optional[dict] = Field(
        None,
        description="Plugin.spec.data.staticData: The static data returned by the Plugin when the class is 'static'. LLM's are adept at understanding the context of json data structures. Try to provide granular and specific data elements.",
    )
    sql_data: Optional[SAMPluginSpecDataSql] = Field(
        None,
        description="Plugin.spec.data.sqlData: The SQL connection and query to use for the Plugin return data when the class is 'sql'",
    )
    api_data: Optional[HttpRequest] = Field(
        None,
        description="Plugin.spec.data.apiData: The rest API connection and endpoint to use for the Plugin return data when the class is 'api'",
    )


class SAMPluginSpec(SAMSpecBase):
    """Smarter API V0 Plugin Manifest Plugin.spec"""

    selector: SAMPluginSpecSelector = Field(
        ..., description="Plugin.spec.selector: the selector logic to use for the Plugin"
    )
    prompt: SAMPluginSpecPrompt = Field(
        ..., description="Plugin.spec.prompt: the LLM prompt engineering to apply to the Plugin"
    )
    data: SAMPluginSpecData = Field(..., description="Plugin.spec.data: the json data returned by the Plugin")

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPluginSpec":
        # Add Plugin Spec-level business rules validations here

        return self
