"""Smarter API Manifest - Plugin.spec"""

import os
import re
from typing import ClassVar, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginCommonSpecSelectorKeys,
)
from smarter.apps.prompt.providers.const import VALID_CHAT_COMPLETION_MODELS
from smarter.common.conf import SettingsDefaults
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase

from .const import MANIFEST_KIND


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 8192  # this is actually the overall max token count for OpenAI chatGPT-4


class SAMPluginCommonSpecSelector(BaseModel):
    """Smarter API Plugin Manifest - Spec - Selector class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".selector"

    directive: str = Field(
        ...,
        description=(
            f"{class_identifier}.directive[str]: Required. the kind of selector directive to use for the {MANIFEST_KIND}. "
            f"Must be one of: {SAMPluginCommonSpecSelectorKeyDirectiveValues.all_values()}"
        ),
    )
    searchTerms: Optional[List[str]] = Field(
        None,
        description=(
            f"{class_identifier}.searchTerms[list]. Optional. The keyword search terms to use when the "
            f"{MANIFEST_KIND} directive is '{SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value}'. "
            "Keywords are most effective when constrained to 1 or 2 words "
            "each and lists are limited to a few dozen items."
        ),
    )

    @field_validator("directive")
    def validate_directive(cls, v) -> str:
        if v not in SAMPluginCommonSpecSelectorKeyDirectiveValues.all_values():
            raise SAMValidationError(
                f"Invalid value found in {cls.class_identifier}.{SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value}: '{v}'. "
                f"Must be one of {SAMPluginCommonSpecSelectorKeyDirectiveValues.all_values()}. "
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
    def validate_business_rules(self) -> "SAMPluginCommonSpecSelector":
        err_desc_searchTerms_name = SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value
        directive_name = SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value

        # 1. searchTerms is required when directive is 'searchTerms'
        if (
            self.directive == SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value
            and self.searchTerms is None
        ):
            raise SAMValidationError(
                f"{self.class_identifier}.{err_desc_searchTerms_name} is required when {self.class_identifier}.{directive_name} is '{err_desc_searchTerms_name}'"
            )

        # 2. searchTerms is not allowed when directive is 'always'
        if (
            self.directive != SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value
            and self.searchTerms is not None
        ):
            raise SAMValidationError(
                f"found {self.class_identifier}.{directive_name} of '{self.directive}' but {self.class_identifier}.{err_desc_searchTerms_name} is only used when {self.class_identifier}.{directive_name} is '{err_desc_searchTerms_name}'"
            )

        return self


class SAMPluginCommonSpecPrompt(BaseModel):
    """Smarter API Plugin Manifest - Spec - Prompt class."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".prompt"

    DEFAULT_PROVIDER: ClassVar[str] = SettingsDefaults.LLM_DEFAULT_PROVIDER
    DEFAULT_MODEL: ClassVar[str] = SettingsDefaults.LLM_DEFAULT_MODEL
    DEFAULT_TEMPERATURE: ClassVar[float] = SettingsDefaults.LLM_DEFAULT_TEMPERATURE
    DEFAULT_MAXTOKENS: ClassVar[int] = SettingsDefaults.LLM_DEFAULT_MAX_TOKENS

    provider: str = Field(
        DEFAULT_PROVIDER,
        description=(
            f"{class_identifier}.provider[str]. Optional. The provider of the LLM. Defaults to {DEFAULT_PROVIDER}. "
            "The provider is the vendor name for the LLM service that will be used to generate the prompt response."
        ),
    )
    systemRole: str = Field(
        ...,
        description=(
            f"{class_identifier}.systemRole[str]. Required. The system role that the {MANIFEST_KIND} will use for the LLM "
            "text completion prompt. Be verbose and specific. Ensure that systemRole accurately conveys to the LLM "
            f"how you want it to use the {MANIFEST_KIND} data that is returned."
        ),
    )
    model: str = Field(
        DEFAULT_MODEL,
        description=(
            f"{class_identifier}.model[str] Optional. The model of the {MANIFEST_KIND}. Defaults to {DEFAULT_MODEL}. "
            f"Must be one of: {VALID_CHAT_COMPLETION_MODELS}"
        ),
    )
    temperature: float = Field(
        DEFAULT_TEMPERATURE,
        ge=0,
        le=1.0,
        description=(
            f"{class_identifier}.temperature[float] Optional. The temperature of the {MANIFEST_KIND}. "
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
            f"The maxTokens of the {MANIFEST_KIND}. Defaults to {DEFAULT_MAXTOKENS}. "
            "The maximum number of tokens the LLM should generate in the prompt response. "
        ),
    )

    @field_validator("provider")
    def validate_provider(cls, v) -> str:

        # FIX NOTE: This is a placeholder for the actual valid providers
        VALID_PROVIDERS = [SettingsDefaults.LLM_DEFAULT_PROVIDER]
        if v not in VALID_PROVIDERS:
            err_desc_me_name = SAMPluginCommonSpecPromptKeys.PROVIDER.value

            raise SAMValidationError(
                f"{cls.class_identifier}.{err_desc_me_name} not found in list of valid providers {VALID_PROVIDERS}"
            )

        return v

    @field_validator("systemRole")
    def validate_systemrole(cls, v) -> str:
        if re.match(SmarterValidator.VALID_CLEAN_STRING_WITH_SPACES, v):
            return v
        err_desc_me_name = SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value

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
        err_desc_me_name = SAMPluginCommonSpecPromptKeys.MODEL.value
        raise SAMValidationError(
            f"Invalid value found in {err_desc_me_name}: '{v}'. Must be one of {VALID_CHAT_COMPLETION_MODELS}"
        )


class SAMPluginCommonSpec(AbstractSAMSpecBase):
    """Smarter API Plugin Manifest Plugin.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    selector: SAMPluginCommonSpecSelector = Field(
        ..., description=f"{class_identifier}.selector[obj]: the selector logic to use for the {MANIFEST_KIND}"
    )
    prompt: SAMPluginCommonSpecPrompt = Field(
        ...,
        description=f"{class_identifier}.prompt[obj]: the LLM prompt engineering to apply to the {MANIFEST_KIND}",
    )
