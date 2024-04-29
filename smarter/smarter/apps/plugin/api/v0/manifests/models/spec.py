"""Smarter API V0 Manifest - Plugin.spec"""

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlparse import parse as sql_parse
from sqlparse.exceptions import SQLParseError

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import HttpRequest, SAMSpecBase, SqlConnection
from smarter.apps.plugin.api.v0.manifests.enum import (
    SAMPluginMetadataClassValues,
    SAMPluginSpecSelectorKeyDirectiveValues,
)
from smarter.common.const import VALID_CHAT_COMPLETION_MODELS
from smarter.lib.django.validators import SmarterValidator


class SAMPluginSpecSelector(BaseModel):
    """Smarter API V0 Plugin Manifest - Spec - Selector class."""

    err_desc_manifest_kind = "Plugin.spec.selector"

    directive: str = Field(
        ...,
        description=(
            f"{err_desc_manifest_kind}.directive[str]: Required. the kind of selector directive to use for the Plugin. "
            f"Must be one of: {SAMPluginSpecSelectorKeyDirectiveValues.all_values()}"
        ),
    )
    searchTerms: Optional[List[str]] = Field(
        None,
        description=(
            f"{err_desc_manifest_kind}.searchTerms[list]. Optional. The keyword search terms to use when the "
            f"Plugin directive is '{SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS.value}'. "
            "Keywords are most effective when constrained to 1 or 2 words "
            "each and lists are limited to a few dozen items."
        ),
    )

    @field_validator("directive")
    def validate_directive(cls, v) -> str:
        if v not in SAMPluginSpecSelectorKeyDirectiveValues.all_values():
            raise SAMValidationError(
                f"Invalid value found in {cls.err_desc_manifest_kind}.directive: {v}. "
                f"Must be one of {SAMPluginSpecSelectorKeyDirectiveValues.all_values()}. "
                "These values are case-sensitive and camelCase."
            )
        return v

    @field_validator("searchTerms")
    def validate_search_terms(cls, v) -> List[str]:
        if isinstance(v, list):
            for search_term in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING, search_term):
                    raise SAMValidationError(
                        f"Invalid value found in {cls.err_desc_manifest_kind}.searchTerms: {search_term}. "
                        "Avoid using characters that are not URL friendly, like spaces and special ascii characters."
                    )
        return v

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPluginSpecSelector":
        eff_desc_search_terms = self.searchTerms.__class__.__name__

        # 1. searchTerms is required when directive is 'searchTerms'
        if self.directive == SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS and self.searchTerms is None:
            raise SAMValidationError(
                f"{self.err_desc_manifest_kind}.{eff_desc_search_terms} is required when {self.err_desc_manifest_kind}.directive is '{eff_desc_search_terms}'"
            )

        # 2. searchTerms is not allowed when directive is 'always'
        if self.directive != SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS and self.searchTerms is not None:
            raise SAMValidationError(
                f"{self.err_desc_manifest_kind}.{eff_desc_search_terms} is only used when {self.err_desc_manifest_kind}.directive is '{eff_desc_search_terms}'"
            )

        return self


class SAMPluginSpecPrompt(BaseModel):
    """Smarter API V0 Plugin Manifest - Spec - Prompt class."""

    err_desc_manifest_kind = "Plugin.spec.prompt"

    DEFAULT_MODEL = "gpt-3.5-turbo-1106"
    DEFAULT_TEMPERATURE = 0.5
    DEFAULT_MAXTOKENS = 2048

    systemRole: str = Field(
        ...,
        description=(
            f"{err_desc_manifest_kind}.systemRole[str]. Required. The system role that the Plugin will use for the LLM "
            "text completion prompt. Be verbose and specific. Ensure that systemRole accurately conveys to the LLM "
            "how you want it to use the Plugin data that is returned."
        ),
    )
    model: str = Field(
        DEFAULT_MODEL,
        description=(
            f"{err_desc_manifest_kind}.model[str] Optional. The model of the Plugin. Defaults to {DEFAULT_MODEL}. "
            f"Must be one of: {VALID_CHAT_COMPLETION_MODELS}"
        ),
    )
    temperature: float = Field(
        DEFAULT_TEMPERATURE,
        gt=0,
        lt=1.0,
        description=(
            f"{err_desc_manifest_kind}.temperature[float] Optional. The temperature of the Plugin. "
            f"Defaults to {DEFAULT_TEMPERATURE}. "
            "Should be between 0 and 1.0. "
            "The higher the temperature, the more creative the response. "
            "The lower the temperature, the more predictable the response."
        ),
    )
    maxTokens: int = Field(
        DEFAULT_MAXTOKENS,
        gt=0,
        description=(
            f"{err_desc_manifest_kind}.maxTokens[int]. Optional. "
            f"The maxTokens of the Plugin. Defaults to {DEFAULT_MAXTOKENS}. "
            "The maximum number of tokens the LLM should generate in the prompt response. "
        ),
    )

    @field_validator("systemRole")
    def validate_systemrole(cls, v) -> str:
        if re.match(SmarterValidator.VALID_CLEAN_STRING, v):
            return v
        err_desc_me_name = cls.systemRole.__class__.__name__
        raise SAMValidationError(f"Invalid characters found in {cls.err_desc_manifest_kind}.{err_desc_me_name}: {v}")

    @field_validator("model")
    def validate_model(cls, v) -> str:
        if v is None:
            return cls.DEFAULT_MODEL
        if v in VALID_CHAT_COMPLETION_MODELS:
            return v
        err_desc_me_name = cls.model.__class__.__name__
        raise SAMValidationError(
            f"Invalid value found in {cls.err_desc_manifest_kind}.{err_desc_me_name}: {v}. Must be one of {VALID_CHAT_COMPLETION_MODELS}"
        )


class SAMPluginSpecDataSql(BaseModel):
    """Smarter API V0 Plugin Manifest Plugin.spec.data.sqlData"""

    err_desc_manifest_kind = "Plugin.spec.data.sqlData"

    connection: SqlConnection = Field(
        ..., description=f"{err_desc_manifest_kind}.connection[obj]: an sql server connection"
    )
    sql: str = Field(
        ...,
        description=f"{err_desc_manifest_kind}.sql[str]: a valid SQL query. Example: 'SELECT * FROM customers WHERE id = 100;'",  # nosec
    )

    @field_validator("sql")
    def validate_sql(cls, v) -> str:
        try:
            sql_parse(v)
        except SQLParseError as e:
            err_desc_sql_name = cls.sql.__class__.__name__
            raise SAMValidationError(
                f"Invalid SQL syntax found in {cls.err_desc_manifest_kind}.{err_desc_sql_name}: {v}. {e}"
            ) from e
        return v


class SAMPluginSpecData(BaseModel):
    """Smarter API V0 Plugin Manifest Plugin.spec.data"""

    err_desc_manifest_kind = "Plugin.spec.data"

    description: str = Field(
        ...,
        description=(
            f"{err_desc_manifest_kind}.description[str]: A narrative description of the Plugin features "
            "that is provided to the LLM as part of a tool_chain dict"
        ),
    )
    staticData: Optional[dict] = Field(
        None,
        description=(
            f"{err_desc_manifest_kind}.staticData[obj]: The static data returned by the Plugin when the "
            f"class is '{SAMPluginMetadataClassValues.STATIC.value}'. LLM's are adept at understanding the context of "
            "json data structures. Try to provide granular and specific data elements."
        ),
    )
    sqlData: Optional[SAMPluginSpecDataSql] = Field(
        None,
        description=(
            f"{err_desc_manifest_kind}.sqlData[obj]: The SQL connection and query to use for the Plugin return data when "
            f"the class is '{SAMPluginMetadataClassValues.SQL.value}'"
        ),
    )
    apiData: Optional[HttpRequest] = Field(
        None,
        description=(
            f"{err_desc_manifest_kind}.apiData[obj]: The rest API connection and endpoint to use for the Plugin "
            f"return data when the class is '{SAMPluginMetadataClassValues.API.value}'"
        ),
    )

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPluginSpecData":
        total_set = bool(self.staticData) + bool(self.sqlData) + bool(self.apiData)

        if total_set != 1:
            static_name = self.staticData.__class__.__name__
            sql_name = self.sqlData.__class__.__name__
            api_name = self.apiData.__class__.__name__

            raise SAMValidationError(
                f"One and only one of {self.err_desc_manifest_kind}.{static_name}, {self.err_desc_manifest_kind}.{sql_name}, or {self.err_desc_manifest_kind}.{api_name} must be provided."
            )

        return self


class SAMPluginSpec(SAMSpecBase):
    """Smarter API V0 Plugin Manifest Plugin.spec"""

    err_desc_manifest_kind = "Plugin.spec"

    selector: SAMPluginSpecSelector = Field(
        ..., description=f"{err_desc_manifest_kind}.selector[obj]: the selector logic to use for the Plugin"
    )
    prompt: SAMPluginSpecPrompt = Field(
        ..., description=f"{err_desc_manifest_kind}.prompt[obj]: the LLM prompt engineering to apply to the Plugin"
    )
    data: SAMPluginSpecData = Field(
        ..., description=f"{err_desc_manifest_kind}.data[obj]: the json data returned by the Plugin"
    )
