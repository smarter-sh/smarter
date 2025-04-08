"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, List, Optional

from pydantic import Field

from smarter.apps.chatbot.manifest.models.chatbot.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SAMChatBotCustomDomain(AbstractSAMSpecBase):
    """Smarter API Chatbot Manifest Chatbot.spec.config.customDomain"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration.customDomain"

    aws_hosted_zone_id: str = Field(
        ...,
        description=(f"{class_identifier}.aws_hosted_zone_id[str]. Required. The AWS hosted zone ID."),
    )
    domain_name: str = Field(
        ...,
        description=(f"{class_identifier}.domain_name[str]. Required. The domain name."),
    )


class SAMChatbotSpecConfig(AbstractSAMSpecBase):
    """Smarter API Chatbot Manifest Chatbot.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    subdomain: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.subdomain[str]. Optional. The subdomain to use for the chatbot."),
    )
    customDomain: Optional[SAMChatBotCustomDomain] = Field(
        None,
        description=(f"{class_identifier}.custom_domain[str]. Optional. The custom domain to use for the chatbot."),
    )
    deployed: bool = Field(
        default=False, description=f"{class_identifier}.deployed[bool]. Required. Whether the chatbot is deployed."
    )

    provider: Optional[str] = Field(
        None,
        description=f"{class_identifier}.provider[str]. Optional. The provider to use for the chatbot. Default: openai.",
    )
    defaultModel: Optional[str] = Field(
        None, description=f"{class_identifier}.default_model[str]. Optional. The default model to use for the chatbot."
    )
    defaultSystemRole: Optional[str] = Field(
        None,
        description=f"{class_identifier}.default_system_role[str]. Optional. The default system prompt to use for the chatbot.",
    )
    defaultTemperature: Optional[float] = Field(
        None,
        description=f"{class_identifier}.default_temperature[float]. Optional. The default temperature to use for the chatbot.",
    )
    defaultMaxTokens: Optional[int] = Field(
        None,
        description=f"{class_identifier}.default_max_tokens[int]. Optional. The default max tokens to use for the chatbot.",
    )

    appName: Optional[str] = Field(
        None, description=f"{class_identifier}.app_name[str]. Optional. The name of the chatbot."
    )
    appAssistant: Optional[str] = Field(
        None, description=f"{class_identifier}.app_assistant[str]. Optional. The assistant name of the chatbot."
    )
    appWelcomeMessage: Optional[str] = Field(
        None, description=f"{class_identifier}.app_welcome_message[str]. Optional. The welcome message of the chatbot."
    )
    appExamplePrompts: Optional[List[str]] = Field(
        None, description=f"{class_identifier}.app_example_prompts[list]. Optional. The example prompts of the chatbot."
    )
    appPlaceholder: Optional[str] = Field(
        None, description=f"{class_identifier}.app_placeholder[str]. Optional. The placeholder of the chatbot."
    )
    appInfoUrl: Optional[str] = Field(
        None, description=f"{class_identifier}.app_info_url[str]. Optional. The info URL of the chatbot."
    )
    appBackgroundImageUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_background_image_url[str]. Optional. The background image URL of the chatbot.",
    )
    appLogoUrl: Optional[str] = Field(
        None, description=f"{class_identifier}.app_logo_url[str]. Optional. The logo URL of the chatbot."
    )
    appFileAttachment: Optional[bool] = Field(
        None,
        description=f"{class_identifier}.app_file_attachment[bool]. Optional. Whether the chatbot supports file attachment.",
    )


class SAMChatbotSpec(AbstractSAMSpecBase):
    """Smarter API Chatbot Manifest Chatbot.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMChatbotSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )
    plugins: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.searchTerms[list]. Optional. The Plugins to add to the " f"{MANIFEST_KIND}.",
    )
    functions: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.functions[list]. Optional. The built-in Smarter Functions to add to the {MANIFEST_KIND}.",
    )
    apiKey: Optional[str] = Field(
        None,
        description=f"{class_identifier}.api_key[str]. Optional. The name of the API key that this chatbot uses for authentication.",
    )
