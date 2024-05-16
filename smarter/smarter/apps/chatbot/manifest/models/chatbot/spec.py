"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, List, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SAMChatbotSpecConfig(AbstractSAMSpecBase):
    """Smarter API Chatbot Manifest Chatbot.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    subdomain = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.subdomain[str]. Optional. The subdomain to use for the chatbot."),
    )
    custom_domain = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.custom_domain[str]. Optional. The custom domain to use for the chatbot."),
    )
    deployed = bool = (
        Field(..., description=(f"{class_identifier}.deployed[bool]. Required. Whether the chatbot is deployed.")),
    )
    default_model = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.default_model[str]. Optional. The default model to use for the chatbot."),
    )
    default_temperature = Optional[float] = Field(
        None,
        description=(
            f"{class_identifier}.default_temperature[float]. Optional. The default temperature to use for the chatbot."
        ),
    )
    default_max_tokens = Optional[int] = Field(
        None,
        description=(
            f"{class_identifier}.default_max_tokens[int]. Optional. The default max tokens to use for the chatbot."
        ),
    )

    app_name = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.app_name[str]. Optional. The name of the chatbot."),
    )
    app_assistant = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.app_assistant[str]. Optional. The assistant name of the chatbot."),
    )
    app_welcome_message = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.app_welcome_message[str]. Optional. The welcome message of the chatbot."),
    )
    app_example_prompts = Optional[List[dict]] = Field(
        None,
        description=(f"{class_identifier}.app_example_prompts[list]. Optional. The example prompts of the chatbot."),
    )
    app_placeholder = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.app_placeholder[str]. Optional. The placeholder of the chatbot."),
    )
    app_info_url = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.app_info_url[str]. Optional. The info URL of the chatbot."),
    )
    app_background_image_url = Optional[str] = Field(
        None,
        description=(
            f"{class_identifier}.app_background_image_url[str]. Optional. The background image URL of the chatbot."
        ),
    )
    app_logo_url = Optional[str] = Field(
        None,
        description=(f"{class_identifier}.app_logo_url[str]. Optional. The logo URL of the chatbot."),
    )
    app_file_attachment = Optional[bool] = Field(
        None,
        description=(
            f"{class_identifier}.app_file_attachment[bool]. Optional. Whether the chatbot supports file attachment."
        ),
    )


class SAMChatbotSpec(AbstractSAMSpecBase):
    """Smarter API Chatbot Manifest Chatbot.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMChatbotSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. Optional. The configuration for the chatbot."),
    )
    plugins: Optional[List[str]] = Field(
        None,
        description=(f"{class_identifier}.searchTerms[list]. Optional. The Plugins to add to the " f"{MANIFEST_KIND}."),
    )
