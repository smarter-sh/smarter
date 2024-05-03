"""Smarter API V0 Manifest - Plugin.spec"""

import os
import re
from typing import ClassVar, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlparse import parse as sql_parse
from sqlparse.exceptions import SQLParseError

from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.api.v0.manifests.models import (
    AbstractSAMSpecBase,
    HttpRequest,
    SqlConnection,
)
from smarter.apps.plugin.api.v0.manifests.enum import (
    SAMPluginMetadataClass,
    SAMPluginMetadataClassValues,
    SAMPluginSpecKeys,
    SAMPluginSpecPromptKeys,
    SAMPluginSpecSelectorKeyDirectiveValues,
    SAMPluginSpecSelectorKeys,
)
from smarter.common.const import VALID_CHAT_COMPLETION_MODELS
from smarter.lib.django.validators import SmarterValidator

from .const import OBJECT_IDENTIFIER


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{OBJECT_IDENTIFIER}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SAMPluginSpecSelector(BaseModel):
    """Smarter API V0 Plugin Manifest - Spec - Selector class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".selector"

    directive: str = Field(
        ...,
        description=(
            f"{class_identifier}.directive[str]: Required. the kind of selector directive to use for the {OBJECT_IDENTIFIER}. "
            f"Must be one of: {SAMPluginSpecSelectorKeyDirectiveValues.all_values()}"
        ),
    )
    searchTerms: Optional[List[str]] = Field(
        None,
        description=(
            f"{class_identifier}.searchTerms[list]. Optional. The keyword search terms to use when the "
            f"{OBJECT_IDENTIFIER} directive is '{SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS.value}'. "
            "Keywords are most effective when constrained to 1 or 2 words "
            "each and lists are limited to a few dozen items."
        ),
    )

    @field_validator("directive")
    def validate_directive(cls, v) -> str:
        if v not in SAMPluginSpecSelectorKeyDirectiveValues.all_values():
            raise SAMValidationError(
                f"Invalid value found in {cls.class_identifier}.{SAMPluginSpecSelectorKeys.DIRECTIVE.value}: '{v}'. "
                f"Must be one of {SAMPluginSpecSelectorKeyDirectiveValues.all_values()}. "
                "These values are case-sensitive and camelCase."
            )
        return v

    @field_validator("searchTerms")
    def validate_search_terms(cls, v) -> List[str]:
        if isinstance(v, list):
            for search_term in v:
                if not re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, search_term):
                    raise SAMValidationError(
                        f"Invalid value found in {cls.class_identifier}.searchTerms: '{search_term}'. "
                        "Avoid using characters that are not URL friendly, like spaces and special ascii characters."
                    )
        return v

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPluginSpecSelector":
        err_desc_searchTerms_name = SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS.value
        directive_name = SAMPluginSpecSelectorKeys.DIRECTIVE.value

        # 1. searchTerms is required when directive is 'searchTerms'
        if self.directive == SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS.value and self.searchTerms is None:
            raise SAMValidationError(
                f"{self.class_identifier}.{err_desc_searchTerms_name} is required when {self.class_identifier}.{directive_name} is '{err_desc_searchTerms_name}'"
            )

        # 2. searchTerms is not allowed when directive is 'always'
        if self.directive != SAMPluginSpecSelectorKeyDirectiveValues.SEARCHTERMS.value and self.searchTerms is not None:
            raise SAMValidationError(
                f"found {self.class_identifier}.{directive_name} of '{self.directive}' but {self.class_identifier}.{err_desc_searchTerms_name} is only used when {self.class_identifier}.{directive_name} is '{err_desc_searchTerms_name}'"
            )

        return self


class SAMPluginSpecPrompt(BaseModel):
    """Smarter API V0 Plugin Manifest - Spec - Prompt class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".prompt"

    DEFAULT_MODEL: ClassVar[str] = "gpt-3.5-turbo-1106"
    DEFAULT_TEMPERATURE: ClassVar[float] = 0.5
    DEFAULT_MAXTOKENS: ClassVar[int] = 2048

    systemRole: str = Field(
        ...,
        description=(
            f"{class_identifier}.systemRole[str]. Required. The system role that the {OBJECT_IDENTIFIER} will use for the LLM "
            "text completion prompt. Be verbose and specific. Ensure that systemRole accurately conveys to the LLM "
            f"how you want it to use the {OBJECT_IDENTIFIER} data that is returned."
        ),
    )
    model: str = Field(
        DEFAULT_MODEL,
        description=(
            f"{class_identifier}.model[str] Optional. The model of the {OBJECT_IDENTIFIER}. Defaults to {DEFAULT_MODEL}. "
            f"Must be one of: {VALID_CHAT_COMPLETION_MODELS}"
        ),
    )
    temperature: float = Field(
        DEFAULT_TEMPERATURE,
        gte=0,
        lte=1.0,
        description=(
            f"{class_identifier}.temperature[float] Optional. The temperature of the {OBJECT_IDENTIFIER}. "
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
            f"{class_identifier}.maxTokens[int]. Optional. "
            f"The maxTokens of the {OBJECT_IDENTIFIER}. Defaults to {DEFAULT_MAXTOKENS}. "
            "The maximum number of tokens the LLM should generate in the prompt response. "
        ),
    )

    @field_validator("systemRole")
    def validate_systemrole(cls, v) -> str:
        if re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, v):
            return v
        err_desc_me_name = SAMPluginSpecPromptKeys.SYSTEMROLE.value

        if len(v) > SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH:  # replace MAX_LENGTH with your maximum length
            raise SAMValidationError(
                f"{cls.class_identifier}.{err_desc_me_name} exceeds maximum length of {SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH}"
            )

        return v

    @field_validator("model")
    def validate_model(cls, v) -> str:
        if v is None:
            return cls.DEFAULT_MODEL
        if v in VALID_CHAT_COMPLETION_MODELS:
            return v
        err_desc_me_name = SAMPluginSpecPromptKeys.MODEL.value
        raise SAMValidationError(
            f"Invalid value found in {cls.err_desc_manifest_kind}.{err_desc_me_name}: '{v}'. Must be one of {VALID_CHAT_COMPLETION_MODELS}"
        )


class SAMPluginSpecDataSql(BaseModel):
    """Smarter API V0 Plugin Manifest Plugin.spec.data.sqlData"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".data.sqlData"

    connection: SqlConnection = Field(..., description=f"{class_identifier}.connection[obj]: an sql server connection")
    sql: str = Field(
        ...,
        description=f"{class_identifier}.sql[str]: a valid SQL query. Example: 'SELECT * FROM customers WHERE id = 100;'",  # nosec
    )

    @field_validator("sql")
    def validate_sql(cls, v) -> str:
        try:
            sql_parse(v)
        except SQLParseError as e:
            err_desc_sql_name = SAMPluginMetadataClass.SQL_DATA.value
            raise SAMValidationError(
                f"Invalid SQL syntax found in {cls.class_identifier}.{err_desc_sql_name}: {v}. {e}"
            ) from e
        return v


class SAMPluginSpecData(BaseModel):
    """Smarter API V0 Plugin Manifest Plugin.spec.data"""

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.{SAMPluginSpecKeys.DATA.value}"

    description: str = Field(
        ...,
        description=(
            f"{class_identifier}.description[str]: A narrative description of the {OBJECT_IDENTIFIER} features "
            "that is provided to the LLM as part of a tool_chain dict"
        ),
    )
    staticData: Optional[dict] = Field(
        None,
        description=(
            f"{class_identifier}.staticData[obj]: The static data returned by the {OBJECT_IDENTIFIER} when the "
            f"class is '{SAMPluginMetadataClassValues.STATIC.value}'. LLM's are adept at understanding the context of "
            "json data structures. Try to provide granular and specific data elements."
        ),
    )
    sqlData: Optional[SAMPluginSpecDataSql] = Field(
        None,
        description=(
            f"{class_identifier}.sqlData[obj]: The SQL connection and query to use for the {OBJECT_IDENTIFIER} return data when "
            f"the class is '{SAMPluginMetadataClassValues.SQL.value}'"
        ),
    )
    apiData: Optional[HttpRequest] = Field(
        None,
        description=(
            f"{class_identifier}.apiData[obj]: The rest API connection and endpoint to use for the {OBJECT_IDENTIFIER} "
            f"return data when the class is '{SAMPluginMetadataClassValues.API.value}'"
        ),
    )

    @model_validator(mode="after")
    def validate_business_rules(self) -> "SAMPluginSpecData":
        total_set = bool(self.staticData) + bool(self.sqlData) + bool(self.apiData)
        set_fields = {
            "staticData": bool(self.staticData),
            "sqlData": bool(self.sqlData),
            "apiData": bool(self.apiData),
        }

        if total_set != 1:
            static_name = SAMPluginMetadataClass.STATIC_DATA.value
            sql_name = SAMPluginMetadataClass.SQL_DATA.value
            api_name = SAMPluginMetadataClass.API_DATA.value

            raise SAMValidationError(
                f"One and only one of {self.class_identifier}.{static_name}, {self.class_identifier}.{sql_name}, or {self.class_identifier}.{api_name} must be provided. Received data for the following: {set_fields}"
            )

        return self


class SAMPluginSpec(AbstractSAMSpecBase):
    """Smarter API V0 Plugin Manifest Plugin.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    selector: SAMPluginSpecSelector = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {OBJECT_IDENTIFIER}"
    )
    prompt: SAMPluginSpecPrompt = Field(
        ...,
        description=f"{class_identifier}.prompt[obj]: the LLM prompt engineering to apply to the {OBJECT_IDENTIFIER}",
    )
    data: SAMPluginSpecData = Field(
        ...,
        description=(
            f"{class_identifier}.data[obj]: the json data returned by the {OBJECT_IDENTIFIER}. "
            f"This should be one of the following kinds: {SAMPluginMetadataClassValues.all_values()}"
        ),
    )
